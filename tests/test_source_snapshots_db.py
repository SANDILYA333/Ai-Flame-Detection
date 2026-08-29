"""Integration tests for DB-005 source snapshots database schema."""

import json
import os
import shutil
import subprocess
import uuid
from typing import Any

import psycopg
import pytest
from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    StringDataRightTruncation,
)

from packages.config import get_settings
from packages.schemas.enums import SnapshotAvailabilityState, SourceRole


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


def _create_test_source(cur: psycopg.Cursor[tuple[Any, ...]]) -> uuid.UUID:
    """Helper to insert a test source and return its UUID."""
    source_name = f"test-src-{uuid.uuid4().hex[:8]}"
    cur.execute(
        """
        INSERT INTO source_registry (name, provider, source_type, role)
        VALUES (%s, 'Test Provider', 'satellite', %s)
        RETURNING id;
        """,
        (source_name, SourceRole.OBSERVATION.value),
    )
    row = cur.fetchone()
    assert row is not None
    return row[0]  # type: ignore[no-any-return]


@pytest.mark.integration
class TestSourceSnapshotsPersistence:
    """Validate source_snapshots schema, constraints, and data integrity."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_source_snapshots_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, and nullability."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "source_id": ("uuid", "NO"),
            "external_version": ("character varying", "YES"),
            "retrieved_at": ("timestamp with time zone", "NO"),
            "acquired_from": ("text", "YES"),
            "request_fingerprint": ("character varying", "YES"),
            "content_hash": ("character varying", "YES"),
            "availability_status": ("character varying", "NO"),
            "error_code": ("character varying", "YES"),
            "metadata_json": ("jsonb", "YES"),
            "created_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'source_snapshots';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in source_snapshots"
                actual_type, actual_null = found[col]
                assert actual_type == expected_type, (
                    f"Column '{col}' type expected {expected_type}, got {actual_type}"
                )
                assert actual_null == expected_null, (
                    f"Column '{col}' nullability expected {expected_null}, "
                    f"got {actual_null}"
                )

    def test_insert_minimal_valid_snapshot(self) -> None:
        """TEST 2: Insert snapshot with only required fields and verify defaults."""
        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            cur.execute(
                """
                INSERT INTO source_snapshots (
                    source_id, availability_status
                ) VALUES (
                    %s, %s
                ) RETURNING id, retrieved_at, availability_status, created_at;
                """,
                (source_id, SnapshotAvailabilityState.AVAILABLE.value),
            )
            row = cur.fetchone()
            assert row is not None
            snapshot_id, retrieved_at, status, created_at = row
            assert isinstance(snapshot_id, uuid.UUID)
            assert retrieved_at.tzinfo is not None
            assert status == "AVAILABLE"
            assert created_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_populated_valid_snapshot(self) -> None:
        """TEST 3: Insert snapshot with all metadata fields populated."""
        content_hash = "a" * 64
        request_fingerprint = "b" * 64
        meta_payload = json.dumps({"etag": "W/12345", "size_bytes": 1048576})

        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            cur.execute(
                """
                INSERT INTO source_snapshots (
                    source_id, external_version, acquired_from,
                    request_fingerprint, content_hash, availability_status,
                    error_code, metadata_json
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    NULL, %s
                ) RETURNING id, source_id, external_version, acquired_from,
                            request_fingerprint, content_hash, availability_status,
                            metadata_json;
                """,
                (
                    source_id,
                    "2026-08-29-NRT",
                    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/...",
                    request_fingerprint,
                    content_hash,
                    SnapshotAvailabilityState.AVAILABLE.value,
                    meta_payload,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == source_id
            assert row[2] == "2026-08-29-NRT"
            assert row[3].startswith("https://firms")
            assert row[4] == request_fingerprint
            assert row[5] == content_hash
            assert row[6] == "AVAILABLE"
            assert row[7] == {"etag": "W/12345", "size_bytes": 1048576}
            conn.rollback()

    def test_foreign_key_to_source_registry_rejected_if_nonexistent(self) -> None:
        """TEST 4: Non-existent source_id is rejected by foreign key constraint."""
        non_existent_source_id = uuid.uuid4()
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO source_snapshots (
                        source_id, availability_status
                    ) VALUES (%s, 'AVAILABLE');
                    """,
                    (non_existent_source_id,),
                )
            conn.rollback()

    def test_foreign_key_on_delete_restrict_blocks_source_deletion(self) -> None:
        """TEST 5: Deleting a source that has snapshots is blocked (RESTRICT)."""
        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            # Insert child snapshot
            cur.execute(
                """
                INSERT INTO source_snapshots (source_id, availability_status)
                VALUES (%s, 'AVAILABLE');
                """,
                (source_id,),
            )

            # Attempt to delete the parent source
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    "DELETE FROM source_registry WHERE id = %s;",
                    (source_id,),
                )
            conn.rollback()

    def test_availability_status_all_valid_states(self) -> None:
        """TEST 6: All SnapshotAvailabilityState values satisfy check constraint."""
        for state in SnapshotAvailabilityState:
            with _get_connection() as conn, conn.cursor() as cur:
                source_id = _create_test_source(cur)
                cur.execute(
                    """
                    INSERT INTO source_snapshots (source_id, availability_status)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (source_id, state.value),
                )
                row = cur.fetchone()
                assert row is not None
                conn.rollback()

    def test_availability_status_rejects_invalid_state(self) -> None:
        """TEST 7: Invalid status strings are rejected by check constraint."""
        invalid_states = ["INVALID", "available", "COMPLETE", "", "SUCCESS"]
        for invalid_state in invalid_states:
            with _get_connection() as conn, conn.cursor() as cur:
                source_id = _create_test_source(cur)
                with pytest.raises(CheckViolation):
                    cur.execute(
                        """
                        INSERT INTO source_snapshots (source_id, availability_status)
                        VALUES (%s, %s);
                        """,
                        (source_id, invalid_state),
                    )
                conn.rollback()

    def test_content_hash_and_fingerprint_length_constraints(self) -> None:
        """TEST 8: Hashes not equal to 64 characters are rejected."""
        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            # Short content hash (63 chars)
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO source_snapshots (
                        source_id, availability_status, content_hash
                    ) VALUES (%s, 'AVAILABLE', %s);
                    """,
                    (source_id, "a" * 63),
                )
            conn.rollback()

        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)
            # Whitespace-padded content hash violating trimmed length = 64
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO source_snapshots (
                        source_id, availability_status, content_hash
                    ) VALUES (%s, 'AVAILABLE', %s);
                    """,
                    (source_id, " " + "a" * 63),
                )
            conn.rollback()

        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)
            # Long request fingerprint (65 chars exceeds column width)
            with pytest.raises((CheckViolation, StringDataRightTruncation)):
                cur.execute(
                    """
                    INSERT INTO source_snapshots (
                        source_id, availability_status, request_fingerprint
                    ) VALUES (%s, 'AVAILABLE', %s);
                    """,
                    (source_id, "x" * 65),
                )
            conn.rollback()

    def test_multiple_snapshots_per_source_cardinality(self) -> None:
        """TEST 9: A single source can have multiple snapshots (1:N)."""
        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            # Insert 3 snapshots for the same source
            for i in range(3):
                cur.execute(
                    """
                    INSERT INTO source_snapshots (
                        source_id, external_version, availability_status
                    ) VALUES (%s, %s, 'AVAILABLE')
                    RETURNING id;
                    """,
                    (source_id, f"v1.0.{i}"),
                )
                assert cur.fetchone() is not None

            # Verify 3 snapshots exist for this source
            cur.execute(
                "SELECT COUNT(*) FROM source_snapshots WHERE source_id = %s;",
                (source_id,),
            )
            count_row = cur.fetchone()
            assert count_row is not None
            assert count_row[0] == 3
            conn.rollback()

    def test_empty_result_and_failure_states_with_error_code(self) -> None:
        """TEST 10: Persist empty results and external failure with error codes."""
        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source(cur)

            # Insert empty result (zero detections found, but HTTP 200)
            cur.execute(
                """
                INSERT INTO source_snapshots (
                    source_id, availability_status, metadata_json
                ) VALUES (%s, 'EMPTY_RESULT', %s)
                RETURNING id, availability_status;
                """,
                (source_id, json.dumps({"record_count": 0})),
            )
            row1 = cur.fetchone()
            assert row1 is not None
            assert row1[1] == "EMPTY_RESULT"

            # Insert failed acquisition (HTTP 503 upstream gateway)
            cur.execute(
                """
                INSERT INTO source_snapshots (
                    source_id, availability_status, error_code, metadata_json
                ) VALUES (%s, 'FAILED', 'HTTP_503_SERVICE_UNAVAILABLE', %s)
                RETURNING id, availability_status, error_code;
                """,
                (source_id, json.dumps({"http_status": 503, "retry_after": 60})),
            )
            row2 = cur.fetchone()
            assert row2 is not None
            assert row2[1] == "FAILED"
            assert row2[2] == "HTTP_503_SERVICE_UNAVAILABLE"
            conn.rollback()
