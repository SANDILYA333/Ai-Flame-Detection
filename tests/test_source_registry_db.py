"""Integration tests for DB-004 source registry database schema."""

import os
import shutil
import subprocess
import uuid
from typing import Any

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from packages.config import get_settings
from packages.schemas.enums import SourceRole


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


def _get_connection() -> psycopg.Connection[tuple[Any, ...]]:
    """Create a raw psycopg connection using project settings."""
    settings = get_settings()
    password = settings.POSTGRES_PASSWORD.get_secret_value()
    port = int(os.getenv("POSTGRES_PORT", str(settings.POSTGRES_PORT)))
    return psycopg.connect(
        host=settings.POSTGRES_HOST,
        port=port,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=password,
        autocommit=False,
    )


@pytest.mark.integration
class TestSourceRegistryPersistence:
    """Validate source_registry schema, constraints, and data integrity."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_source_registry_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, and nullability."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "name": ("character varying", "NO"),
            "provider": ("character varying", "NO"),
            "source_type": ("character varying", "NO"),
            "role": ("character varying", "NO"),
            "observation_family": ("character varying", "YES"),
            "coverage_notes": ("text", "YES"),
            "access_method": ("character varying", "YES"),
            "auth_required": ("boolean", "NO"),
            "license_notes": ("text", "YES"),
            "rate_limit_notes": ("text", "YES"),
            "fallback_source_id": ("uuid", "YES"),
            "status": ("character varying", "NO"),
            "created_at": ("timestamp with time zone", "NO"),
            "updated_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'source_registry';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in source_registry"
                actual_type, actual_null = found[col]
                assert actual_type == expected_type, (
                    f"Column '{col}' type expected {expected_type}, got {actual_type}"
                )
                assert actual_null == expected_null, (
                    f"Column '{col}' nullability expected {expected_null}, "
                    f"got {actual_null}"
                )

    def test_insert_minimal_valid_source(self) -> None:
        """TEST 2: Insert source with only required fields and verify defaults."""
        source_name = f"test-minimal-source-{uuid.uuid4().hex[:8]}"
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO source_registry (
                    name, provider, source_type, role
                ) VALUES (
                    %s, %s, %s, %s
                ) RETURNING id, auth_required, status, created_at, updated_at;
                """,
                (source_name, "NASA", "satellite", SourceRole.OBSERVATION.value),
            )
            row = cur.fetchone()
            assert row is not None
            source_id, auth_required, status, created_at, updated_at = row
            assert isinstance(source_id, uuid.UUID)
            assert auth_required is False
            assert status == "active"
            assert created_at.tzinfo is not None
            assert updated_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_populated_valid_source(self) -> None:
        """TEST 3: Insert source with all fields populated."""
        source_name = f"test-full-source-{uuid.uuid4().hex[:8]}"
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO source_registry (
                    name, provider, source_type, role,
                    observation_family, coverage_notes, access_method,
                    auth_required, license_notes, rate_limit_notes,
                    status
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s
                ) RETURNING id, name, provider, role, observation_family,
                            auth_required, status;
                """,
                (
                    source_name,
                    "NASA FIRMS",
                    "satellite_thermal",
                    SourceRole.OBSERVATION.value,
                    "thermal_infrared",
                    "Global coverage, 375m spatial resolution, ~12h revisit",
                    "REST API / CSV Download",
                    True,
                    "NASA Open Data Policy, attribution requested",
                    "Max 10 requests per minute per MAP_KEY",
                    "active",
                ),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == source_name
            assert row[2] == "NASA FIRMS"
            assert row[3] == SourceRole.OBSERVATION.value
            assert row[4] == "thermal_infrared"
            assert row[5] is True
            assert row[6] == "active"
            conn.rollback()

    def test_unique_name_constraint(self) -> None:
        """TEST 4: Duplicate source names are rejected by unique constraint."""
        source_name = f"unique-source-{uuid.uuid4().hex[:8]}"
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO source_registry (name, provider, source_type, role)
                VALUES (%s, 'Provider A', 'type_a', 'OBSERVATION');
                """,
                (source_name,),
            )
            with pytest.raises(UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO source_registry (name, provider, source_type, role)
                    VALUES (%s, 'Provider B', 'type_b', 'CONTEXT');
                    """,
                    (source_name,),
                )
            conn.rollback()

    def test_role_check_constraint_all_valid_roles(self) -> None:
        """TEST 5: All 10 canonical SourceRole enum values satisfy check constraint."""
        for role in SourceRole:
            source_name = f"test-role-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
            with _get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO source_registry (name, provider, source_type, role)
                    VALUES (%s, 'Test Provider', 'test_type', %s)
                    RETURNING id;
                    """,
                    (source_name, role.value),
                )
                row = cur.fetchone()
                assert row is not None
                conn.rollback()

    def test_role_check_constraint_rejects_invalid_role(self) -> None:
        """TEST 6: Invalid role strings are rejected by check constraint."""
        invalid_roles = ["INVALID_ROLE", "observation", "ground_truth", "", "UNKNOWN"]
        for invalid_role in invalid_roles:
            source_name = f"test-invalid-role-{uuid.uuid4().hex[:8]}"
            with _get_connection() as conn, conn.cursor() as cur:
                with pytest.raises(CheckViolation):
                    cur.execute(
                        """
                        INSERT INTO source_registry (name, provider, source_type, role)
                        VALUES (%s, 'Test Provider', 'test_type', %s);
                        """,
                        (source_name, invalid_role),
                    )
                conn.rollback()

    def test_non_empty_string_check_constraints(self) -> None:
        """TEST 7: Empty or whitespace-only strings are rejected for required fields."""
        fields_to_test = [
            ("name", ("", "Provider", "satellite", "OBSERVATION", "active")),
            ("name_sp", ("   ", "Provider", "satellite", "OBSERVATION", "active")),
            ("prov", ("valid_1", "", "satellite", "OBSERVATION", "active")),
            ("prov_sp", ("valid_2", "  ", "satellite", "OBSERVATION", "active")),
            ("type", ("valid_3", "Provider", "", "OBSERVATION", "active")),
            ("type_sp", ("valid_4", "Provider", " ", "OBSERVATION", "active")),
            ("status", ("valid_5", "Provider", "satellite", "OBSERVATION", "")),
            ("status_sp", ("valid_6", "Provider", "satellite", "OBSERVATION", "  ")),
        ]

        for _desc, (name, provider, source_type, role, status) in fields_to_test:
            with _get_connection() as conn, conn.cursor() as cur:
                with pytest.raises(CheckViolation):
                    cur.execute(
                        """
                        INSERT INTO source_registry (
                            name, provider, source_type, role, status
                        ) VALUES (%s, %s, %s, %s, %s);
                        """,
                        (name, provider, source_type, role, status),
                    )
                conn.rollback()

    def test_fallback_source_foreign_key_and_null_on_delete(self) -> None:
        """TEST 8: Self-referential fallback_source_id links and sets NULL on delete."""
        primary_name = f"primary-source-{uuid.uuid4().hex[:8]}"
        fallback_name = f"fallback-source-{uuid.uuid4().hex[:8]}"

        with _get_connection() as conn, conn.cursor() as cur:
            # Insert fallback source
            cur.execute(
                """
                INSERT INTO source_registry (name, provider, source_type, role)
                VALUES (%s, 'Fallback Provider', 'satellite', 'OBSERVATION')
                RETURNING id;
                """,
                (fallback_name,),
            )
            fallback_row = cur.fetchone()
            assert fallback_row is not None
            fallback_id = fallback_row[0]

            # Insert primary source referencing fallback
            cur.execute(
                """
                INSERT INTO source_registry (
                    name, provider, source_type, role, fallback_source_id
                ) VALUES (%s, 'Primary Provider', 'satellite', 'OBSERVATION', %s)
                RETURNING id, fallback_source_id;
                """,
                (primary_name, fallback_id),
            )
            primary_row = cur.fetchone()
            assert primary_row is not None
            primary_id, linked_fallback_id = primary_row
            assert linked_fallback_id == fallback_id

            # Delete the fallback source
            cur.execute(
                "DELETE FROM source_registry WHERE id = %s;",
                (fallback_id,),
            )

            # Check that primary source's fallback_source_id is set to NULL
            cur.execute(
                "SELECT fallback_source_id FROM source_registry WHERE id = %s;",
                (primary_id,),
            )
            res_row = cur.fetchone()
            assert res_row is not None
            assert res_row[0] is None

            conn.rollback()

    def test_fallback_source_cannot_be_self(self) -> None:
        """TEST 9: A source cannot designate itself as its own fallback_source_id."""
        source_id = uuid.uuid4()
        source_name = f"self-fallback-source-{uuid.uuid4().hex[:8]}"

        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO source_registry (
                        id, name, provider, source_type, role, fallback_source_id
                    ) VALUES (%s, %s, 'Provider', 'satellite', 'OBSERVATION', %s);
                    """,
                    (source_id, source_name, source_id),
                )
            conn.rollback()

    def test_fallback_source_nonexistent_foreign_key_rejected(self) -> None:
        """TEST 10: Non-existent fallback UUID is rejected by FK constraint."""
        non_existent_id = uuid.uuid4()
        source_name = f"fk-fail-source-{uuid.uuid4().hex[:8]}"

        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO source_registry (
                        name, provider, source_type, role, fallback_source_id
                    ) VALUES (%s, 'Provider', 'satellite', 'OBSERVATION', %s);
                    """,
                    (source_name, non_existent_id),
                )
            conn.rollback()
