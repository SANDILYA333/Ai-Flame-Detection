"""Integration tests for DB-006 source records database schema."""

import json
import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    UniqueViolation,
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


def _create_test_source_and_snapshot(
    cur: psycopg.Cursor[tuple[Any, ...]],
) -> tuple[uuid.UUID, uuid.UUID]:
    """Helper to insert a test source and snapshot, returning their UUIDs."""
    source_name = f"test-src-{uuid.uuid4().hex[:8]}"
    cur.execute(
        """
        INSERT INTO source_registry (name, provider, source_type, role)
        VALUES (%s, 'Test Provider', 'satellite', %s)
        RETURNING id;
        """,
        (source_name, SourceRole.OBSERVATION.value),
    )
    row_src = cur.fetchone()
    assert row_src is not None
    source_id: uuid.UUID = row_src[0]

    cur.execute(
        """
        INSERT INTO source_snapshots (
            source_id, external_version, availability_status
        ) VALUES (
            %s, 'v2026.1', %s
        ) RETURNING id;
        """,
        (source_id, SnapshotAvailabilityState.AVAILABLE.value),
    )
    row_snap = cur.fetchone()
    assert row_snap is not None
    snapshot_id: uuid.UUID = row_snap[0]

    return source_id, snapshot_id


@pytest.mark.integration
class TestSourceRecordsPersistence:
    """Validate source_records schema, PostGIS geometry, constraints, and provenance."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_source_records_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, nullability, and PostGIS metadata."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "source_snapshot_id": ("uuid", "NO"),
            "external_record_id": ("character varying", "YES"),
            "raw_artifact_uri": ("text", "YES"),
            "record_hash": ("character varying", "NO"),
            "record_time": ("timestamp with time zone", "YES"),
            "geometry": ("USER-DEFINED", "YES"),
            "raw_metadata_json": ("jsonb", "YES"),
            "created_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'source_records';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in source_records"
                actual_type, actual_null = found[col]
                assert actual_type == expected_type, (
                    f"Column '{col}' type expected {expected_type}, got {actual_type}"
                )
                assert actual_null == expected_null, (
                    f"Column '{col}' nullability expected {expected_null}, "
                    f"got {actual_null}"
                )

            # Verify PostGIS geometry_columns metadata registration
            cur.execute(
                """
                SELECT f_geometry_column, coord_dimension, srid, type
                FROM geometry_columns
                WHERE f_table_name = 'source_records';
                """
            )
            geom_meta = cur.fetchone()
            assert geom_meta is not None
            assert geom_meta[0] == "geometry"
            assert geom_meta[1] == 2
            assert geom_meta[2] == 4326
            assert geom_meta[3] == "GEOMETRY"

    def test_insert_minimal_valid_record(self) -> None:
        """TEST 2: Insert record with only required fields and verify defaults."""
        record_hash = "c" * 64
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)

            cur.execute(
                """
                INSERT INTO source_records (
                    source_snapshot_id, record_hash
                ) VALUES (
                    %s, %s
                ) RETURNING id, source_snapshot_id, record_hash, created_at;
                """,
                (snapshot_id, record_hash),
            )
            row = cur.fetchone()
            assert row is not None
            record_id, snap_id, r_hash, created_at = row
            assert isinstance(record_id, uuid.UUID)
            assert snap_id == snapshot_id
            assert r_hash == record_hash
            assert created_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_populated_record_with_point_geometry(self) -> None:
        """TEST 3: Insert record with all metadata and Point geometry in EPSG:4326."""
        record_hash = "d" * 64
        record_time = datetime(2026, 8, 29, 10, 15, 30, tzinfo=UTC)
        raw_meta = json.dumps(
            {
                "brightness_ti4": 345.6,
                "frp": 12.4,
                "confidence": "nominal",
                "scan": 0.38,
                "track": 0.36,
            }
        )

        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)

            cur.execute(
                """
                INSERT INTO source_records (
                    source_snapshot_id, external_record_id, raw_artifact_uri,
                    record_hash, record_time, geometry, raw_metadata_json
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326), %s
                ) RETURNING id, external_record_id, raw_artifact_uri, record_hash,
                            record_time, ST_AsText(geometry), ST_SRID(geometry),
                            raw_metadata_json;
                """,
                (
                    snapshot_id,
                    "FIRMS-ROW-987654",
                    "s3://sih26162-raw-artifacts/2026-08-29/viirs_nrt.csv",
                    record_hash,
                    record_time,
                    raw_meta,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == "FIRMS-ROW-987654"
            assert row[2].startswith("s3://sih26162-raw-artifacts")
            assert row[3] == record_hash
            assert row[4] == record_time
            assert row[5] == "POINT(77.209 28.6139)"
            assert row[6] == 4326
            assert row[7] == {
                "brightness_ti4": 345.6,
                "frp": 12.4,
                "confidence": "nominal",
                "scan": 0.38,
                "track": 0.36,
            }
            conn.rollback()

    def test_insert_polygon_geometry(self) -> None:
        """TEST 4: Insert record with Polygon geometry in EPSG:4326."""
        record_hash = "e" * 64
        poly_wkt = "POLYGON((77.0 28.0, 77.5 28.0, 77.5 28.5, 77.0 28.5, 77.0 28.0))"
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)

            cur.execute(
                """
                INSERT INTO source_records (
                    source_snapshot_id, record_hash, geometry
                ) VALUES (
                    %s, %s,
                    ST_SetSRID(ST_PolygonFromText(%s), 4326)
                ) RETURNING id, ST_GeometryType(geometry), ST_SRID(geometry);
                """,
                (snapshot_id, record_hash, poly_wkt),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == "ST_Polygon"
            assert row[2] == 4326
            conn.rollback()

    def test_foreign_key_to_source_snapshots_rejected_if_nonexistent(self) -> None:
        """TEST 5: Non-existent snapshot_id is rejected by foreign key constraint."""
        non_existent_snapshot_id = uuid.uuid4()
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO source_records (
                        source_snapshot_id, record_hash
                    ) VALUES (%s, %s);
                    """,
                    (non_existent_snapshot_id, "f" * 64),
                )
            conn.rollback()

    def test_foreign_key_on_delete_restrict_blocks_snapshot_deletion(self) -> None:
        """TEST 6: Deleting a snapshot that has records is blocked (RESTRICT)."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)

            # Insert child record
            cur.execute(
                """
                INSERT INTO source_records (source_snapshot_id, record_hash)
                VALUES (%s, %s);
                """,
                (snapshot_id, "1" * 64),
            )

            # Attempt to delete the parent snapshot
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    "DELETE FROM source_snapshots WHERE id = %s;",
                    (snapshot_id,),
                )
            conn.rollback()

    def test_composite_uniqueness_constraint(self) -> None:
        """TEST 7: Duplicate (snapshot_id, record_hash) fails; cross-snapshot passes."""
        record_hash = "2" * 64
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id_1 = _create_test_source_and_snapshot(cur)
            _, snapshot_id_2 = _create_test_source_and_snapshot(cur)

            # First insert in snapshot 1 succeeds
            cur.execute(
                """
                INSERT INTO source_records (source_snapshot_id, record_hash)
                VALUES (%s, %s) RETURNING id;
                """,
                (snapshot_id_1, record_hash),
            )
            assert cur.fetchone() is not None

            # Duplicate insert in snapshot 1 MUST fail with UniqueViolation
            with pytest.raises(UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO source_records (source_snapshot_id, record_hash)
                    VALUES (%s, %s);
                    """,
                    (snapshot_id_1, record_hash),
                )
            conn.rollback()

        # Same record_hash in snapshot 2 MUST succeed (cross-snapshot duplicate allowed)
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id_1 = _create_test_source_and_snapshot(cur)
            _, snapshot_id_2 = _create_test_source_and_snapshot(cur)

            cur.execute(
                """
                INSERT INTO source_records (source_snapshot_id, record_hash)
                VALUES (%s, %s) RETURNING id;
                """,
                (snapshot_id_1, record_hash),
            )
            assert cur.fetchone() is not None

            cur.execute(
                """
                INSERT INTO source_records (source_snapshot_id, record_hash)
                VALUES (%s, %s) RETURNING id;
                """,
                (snapshot_id_2, record_hash),
            )
            assert cur.fetchone() is not None
            conn.rollback()

    def test_record_hash_length_constraint(self) -> None:
        """TEST 8: Hash length not equal to 64 characters is rejected."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)

            # Short hash (63 chars)
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO source_records (source_snapshot_id, record_hash)
                    VALUES (%s, %s);
                    """,
                    (snapshot_id, "3" * 63),
                )
            conn.rollback()

        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id = _create_test_source_and_snapshot(cur)
            # Whitespace-padded hash (64 chars with leading space)
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO source_records (source_snapshot_id, record_hash)
                    VALUES (%s, %s);
                    """,
                    (snapshot_id, " " + "3" * 63),
                )
            conn.rollback()

    def test_temporal_distinction_observed_vs_retrieved_vs_created(self) -> None:
        """TEST 9: Distinguish observation, snapshot retrieval, and DB insertion."""
        observed_time = datetime(2026, 8, 29, 8, 30, 0, tzinfo=UTC)
        retrieved_time = datetime(2026, 8, 29, 9, 0, 0, tzinfo=UTC)

        with _get_connection() as conn, conn.cursor() as cur:
            source_id = _create_test_source_and_snapshot(cur)[0]

            # Insert snapshot with explicit retrieved_at
            cur.execute(
                """
                INSERT INTO source_snapshots (
                    source_id, retrieved_at, availability_status
                ) VALUES (
                    %s, %s, 'AVAILABLE'
                ) RETURNING id, retrieved_at;
                """,
                (source_id, retrieved_time),
            )
            snap_row = cur.fetchone()
            assert snap_row is not None
            snapshot_id, snap_retrieved_at = snap_row

            # Insert record with distinct observed_time
            cur.execute(
                """
                INSERT INTO source_records (
                    source_snapshot_id, record_hash, record_time
                ) VALUES (
                    %s, %s, %s
                ) RETURNING id, record_time, created_at;
                """,
                (snapshot_id, "4" * 64, observed_time),
            )
            rec_row = cur.fetchone()
            assert rec_row is not None
            _, rec_time, rec_created_at = rec_row

            assert rec_time == observed_time
            assert snap_retrieved_at == retrieved_time
            assert rec_time != snap_retrieved_at
            assert rec_created_at.tzinfo is not None
            conn.rollback()

    def test_full_provenance_chain(self) -> None:
        """TEST 10: Validate 3-tier lineage: source -> snapshot -> record."""
        record_hash_1 = "a" * 64
        record_hash_2 = "b" * 64

        coords = [(77.2, 28.6), (77.3, 28.7)]
        with _get_connection() as conn, conn.cursor() as cur:
            source_id, snapshot_id = _create_test_source_and_snapshot(cur)

            # Insert 2 records for this snapshot
            for i, r_hash in enumerate([record_hash_1, record_hash_2]):
                lon, lat = coords[i]
                cur.execute(
                    """
                    INSERT INTO source_records (
                        source_snapshot_id, external_record_id, record_hash,
                        geometry
                    ) VALUES (
                        %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    );
                    """,
                    (snapshot_id, f"EXT-REC-{i}", r_hash, lon, lat),
                )

            # Execute 3-tier joined lineage query
            cur.execute(
                """
                SELECT
                    sr.name AS source_name,
                    sr.provider AS source_provider,
                    sr.role AS source_role,
                    ss.id AS snapshot_id,
                    ss.external_version AS snapshot_version,
                    ss.availability_status AS snapshot_status,
                    rec.id AS record_id,
                    rec.external_record_id,
                    rec.record_hash,
                    ST_AsText(rec.geometry) AS geom_wkt
                FROM source_records rec
                JOIN source_snapshots ss ON rec.source_snapshot_id = ss.id
                JOIN source_registry sr ON ss.source_id = sr.id
                WHERE sr.id = %s
                ORDER BY rec.external_record_id;
                """,
                (source_id,),
            )
            rows = cur.fetchall()
            assert len(rows) == 2

            # Assert complete lineage provenance data
            assert rows[0][0].startswith("test-src-")
            assert rows[0][1] == "Test Provider"
            assert rows[0][2] == "OBSERVATION"
            assert rows[0][3] == snapshot_id
            assert rows[0][4] == "v2026.1"
            assert rows[0][5] == "AVAILABLE"
            assert rows[0][7] == "EXT-REC-0"
            assert rows[0][8] == record_hash_1
            assert rows[0][9] == "POINT(77.2 28.6)"

            assert rows[1][7] == "EXT-REC-1"
            assert rows[1][8] == record_hash_2
            assert rows[1][9] == "POINT(77.3 28.7)"

            conn.rollback()
