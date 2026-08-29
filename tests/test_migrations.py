"""Integration smoke tests for DB-002 Alembic Migration Framework.

These tests validate that the database migration lifecycle executes
reproducibly, idempotently, and reversibly against the PostgreSQL/PostGIS database.

Marked with `integration` and skipped cleanly if the database container is offline.
"""

import os
import shutil
import subprocess

import pytest


def _is_docker_and_container_available() -> bool:
    """Check if docker CLI is present and postgres-postgis container is running."""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return "postgres-postgis" in res.stdout
    except Exception:
        return False


def _run_alembic_cmd(
    args: list[str], env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Execute an alembic command using uv run."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = ["uv", "run", "alembic", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=15,
    )


@pytest.mark.integration
class TestAlembicMigrationFramework:
    """Validate Alembic migration framework lifecycle."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip tests if the Docker Compose database is not active."""
        if not _is_docker_and_container_available():
            pytest.skip(
                "postgres-postgis container is not running. "
                "Run 'docker compose up -d' to execute DB-002 migration tests."
            )

    def test_alembic_current_and_history(self) -> None:
        """TEST 1 & 2: Verify Alembic history and current commands succeed."""
        # Ensure we are at head first
        upgrade_res = _run_alembic_cmd(["upgrade", "head"])
        assert upgrade_res.returncode == 0, f"Upgrade failed: {upgrade_res.stderr}"

        # Current revision check
        current_res = _run_alembic_cmd(["current"])
        assert current_res.returncode == 0, f"Current failed: {current_res.stderr}"
        assert "0007_thermal_events" in current_res.stdout

        # History check
        history_res = _run_alembic_cmd(["history"])
        assert history_res.returncode == 0, f"History failed: {history_res.stderr}"
        assert "0007_thermal_events" in history_res.stdout
        assert "0006_detections" in history_res.stdout
        assert "0005_source_records" in history_res.stdout
        assert "0004_source_snapshots" in history_res.stdout
        assert "0003_source_registry" in history_res.stdout
        assert "0002_scientific_contracts" in history_res.stdout
        assert "0001_baseline" in history_res.stdout

    def test_alembic_downgrade_and_reupgrade_lifecycle(self) -> None:
        """TEST 3 & 4: Verify migration reversal (downgrade) and re-upgrade."""
        # Downgrade 1 step to 0006_detections
        down_one_res = _run_alembic_cmd(["downgrade", "-1"])
        assert down_one_res.returncode == 0, (
            f"Downgrade -1 failed: {down_one_res.stderr}"
        )

        current_res = _run_alembic_cmd(["current"])
        assert current_res.returncode == 0
        assert "0006_detections" in current_res.stdout
        assert "0007_thermal_events" not in current_res.stdout

        # Downgrade to base
        down_res = _run_alembic_cmd(["downgrade", "base"])
        assert down_res.returncode == 0, f"Downgrade base failed: {down_res.stderr}"

        # Check current is now empty (base)
        current_base_res = _run_alembic_cmd(["current"])
        assert current_base_res.returncode == 0
        assert "0007_thermal_events" not in current_base_res.stdout
        assert "0006_detections" not in current_base_res.stdout
        assert "0005_source_records" not in current_base_res.stdout
        assert "0004_source_snapshots" not in current_base_res.stdout
        assert "0003_source_registry" not in current_base_res.stdout
        assert "0002_scientific_contracts" not in current_base_res.stdout

        # Re-upgrade to head
        reup_res = _run_alembic_cmd(["upgrade", "head"])
        assert reup_res.returncode == 0, f"Re-upgrade failed: {reup_res.stderr}"

        # Check current is restored to head
        current_restored = _run_alembic_cmd(["current"])
        assert current_restored.returncode == 0
        assert "0007_thermal_events" in current_restored.stdout

    def test_migration_idempotency(self) -> None:
        """TEST 5: Verify running upgrade on an already-upgraded DB is a no-op."""
        res1 = _run_alembic_cmd(["upgrade", "head"])
        assert res1.returncode == 0

        res2 = _run_alembic_cmd(["upgrade", "head"])
        assert res2.returncode == 0
        assert "Running upgrade" not in res2.stdout

    def test_alembic_version_table_in_database(self) -> None:
        """TEST 6: Verify alembic_version table exists and tracks revision."""
        db_name = os.getenv("POSTGRES_DB", "sih26162")
        db_user = os.getenv("POSTGRES_USER", "sih_user")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres-postgis",
            "psql",
            "-U",
            db_user,
            "-d",
            db_name,
            "-tAc",
            "SELECT version_num FROM alembic_version;",
        ]
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=10
        )
        assert res.stdout.strip() == "0007_thermal_events"

    def test_migration_failure_visibility(self) -> None:
        """TEST 7: Verify invalid connection URL produces visible nonzero exit."""
        bad_url = "postgresql+psycopg://baduser:badpass@127.0.0.1:54321/nonexistent"
        res = _run_alembic_cmd(["current"], env_overrides={"DATABASE_URL": bad_url})
        assert res.returncode != 0, (
            "Alembic should fail when connecting to invalid database URL"
        )
