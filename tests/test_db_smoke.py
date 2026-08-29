"""Integration smoke tests for DB-001 PostGIS Compose service.

These tests validate that the local PostgreSQL + PostGIS container infrastructure
is reachable, healthy, has the PostGIS extension loaded, and successfully
computes spatial operations.

Integration tests are marked with `integration` and require a running Docker
service (`docker compose up -d`). If the service is not running, they skip cleanly
to ensure isolated unit tests remain green.
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


def _run_psql_cmd(sql: str) -> str:
    """Execute a psql query inside the postgres-postgis container."""
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
        sql,
    ]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return res.stdout.strip()


@pytest.mark.integration
class TestPostgisInfrastructure:
    """Validate PostGIS local Compose service infrastructure."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip tests if the Docker Compose service is not active."""
        if not _is_docker_and_container_available():
            pytest.skip(
                "postgres-postgis container is not running. "
                "Run 'docker compose up -d' to execute DB-001 integration tests."
            )

    def test_postgres_connectivity(self) -> None:
        """TEST 1: Verify PostgreSQL connection succeeds."""
        db_name = os.getenv("POSTGRES_DB", "sih26162")
        db_user = os.getenv("POSTGRES_USER", "sih_user")
        res = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres-postgis",
                "pg_isready",
                "-U",
                db_user,
                "-d",
                db_name,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert res.returncode == 0, f"pg_isready failed: {res.stderr}"

    def test_postgis_extension_exists(self) -> None:
        """TEST 2: Verify PostGIS extension is installed in pg_extension."""
        out = _run_psql_cmd(
            "SELECT extname FROM pg_extension WHERE extname = 'postgis';"
        )
        assert out == "postgis", f"Expected 'postgis', got '{out}'"

    def test_postgis_version_query(self) -> None:
        """TEST 3: Verify PostGIS version can be queried."""
        out = _run_psql_cmd("SELECT PostGIS_Version();")
        assert len(out) > 0, "PostGIS version returned empty string"
        assert out.startswith("3."), f"Expected PostGIS 3.x, got '{out}'"

    def test_postgis_spatial_expression(self) -> None:
        """TEST 4: Verify basic PostGIS spatial operation executes successfully."""
        out = _run_psql_cmd("SELECT ST_AsText(ST_Point(77.2090, 28.6139, 4326));")
        assert out == "POINT(77.209 28.6139)", f"Unexpected point output: '{out}'"

    def test_temporary_table_lifecycle_and_cleanup(self) -> None:
        """TEST 5: Verify ephemeral DDL execution without leaving tables behind."""
        table_name = "_db001_smoke_check"
        try:
            _run_psql_cmd(
                f"CREATE TEMP TABLE {table_name} "
                "(id INT PRIMARY KEY, geom GEOMETRY(Point, 4326));"
            )
            # Temp table is automatically isolated to session and dropped
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Temporary spatial table operation failed: {e.stderr}")
