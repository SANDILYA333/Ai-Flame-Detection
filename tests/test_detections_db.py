"""Integration tests for DB-007 canonical detections database schema."""

import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation

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


def _create_test_lineage(
    cur: psycopg.Cursor[tuple[Any, ...]],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Helper to insert registered source, snapshot, and raw source record."""
    source_name = f"test-src-{uuid.uuid4().hex[:8]}"
    cur.execute(
        """
        INSERT INTO source_registry (name, provider, source_type, role)
        VALUES (%s, 'NASA FIRMS', 'satellite', %s)
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
            %s, '2026.08.29', %s
        ) RETURNING id;
        """,
        (source_id, SnapshotAvailabilityState.AVAILABLE.value),
    )
    row_snap = cur.fetchone()
    assert row_snap is not None
    snapshot_id: uuid.UUID = row_snap[0]

    record_hash = "a" * 64
    cur.execute(
        """
        INSERT INTO source_records (
            source_snapshot_id, external_record_id, record_hash,
            geometry
        ) VALUES (
            %s, 'RAW-REC-001', %s,
            ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326)
        ) RETURNING id;
        """,
        (snapshot_id, record_hash),
    )
    row_rec = cur.fetchone()
    assert row_rec is not None
    record_id: uuid.UUID = row_rec[0]

    return source_id, snapshot_id, record_id


@pytest.mark.integration
class TestDetectionsPersistence:
    """Validate detections schema, PostGIS point geometry, units, and provenance."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_detections_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, nullability, and PostGIS metadata."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "source_record_id": ("uuid", "NO"),
            "source_snapshot_id": ("uuid", "NO"),
            "source": ("character varying", "NO"),
            "satellite": ("character varying", "NO"),
            "instrument": ("character varying", "NO"),
            "product_type": ("character varying", "NO"),
            "product_version": ("character varying", "NO"),
            "acquired_at": ("timestamp with time zone", "NO"),
            "ingested_at": ("timestamp with time zone", "NO"),
            "latitude": ("double precision", "NO"),
            "longitude": ("double precision", "NO"),
            "geometry": ("USER-DEFINED", "NO"),
            "frp_mw": ("double precision", "YES"),
            "brightness_ti4_k": ("double precision", "YES"),
            "brightness_ti5_k": ("double precision", "YES"),
            "confidence_raw": ("character varying", "YES"),
            "day_night": ("character varying", "YES"),
            "scan": ("double precision", "YES"),
            "track": ("double precision", "YES"),
            "raw_identifier": ("character varying", "YES"),
            "raw_hash": ("character varying", "NO"),
            "quality_status": ("character varying", "YES"),
            "created_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'detections';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in detections"
                actual_type, actual_null = found[col]
                assert actual_type == expected_type, (
                    f"Column '{col}' type expected {expected_type}, got {actual_type}"
                )
                assert actual_null == expected_null, (
                    f"Column '{col}' nullability expected {expected_null}, "
                    f"got {actual_null}"
                )

            # Verify PostGIS geometry_columns metadata registration as Point
            cur.execute(
                """
                SELECT f_geometry_column, coord_dimension, srid, type
                FROM geometry_columns
                WHERE f_table_name = 'detections';
                """
            )
            geom_meta = cur.fetchone()
            assert geom_meta is not None
            assert geom_meta[0] == "geometry"
            assert geom_meta[1] == 2
            assert geom_meta[2] == 4326
            assert geom_meta[3] == "POINT"

    def test_insert_minimal_valid_detection(self) -> None:
        """TEST 2: Insert detection with required fields and verify defaults."""
        raw_hash = "b" * 64
        acquired_time = datetime(2026, 8, 29, 10, 15, 0, tzinfo=UTC)

        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, record_id = _create_test_lineage(cur)

            cur.execute(
                """
                INSERT INTO detections (
                    source_record_id, source_snapshot_id, source,
                    satellite, instrument, product_type, product_version,
                    acquired_at, latitude, longitude, geometry, raw_hash
                ) VALUES (
                    %s, %s, 'firms',
                    'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                    %s, 28.6139, 77.2090,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326), %s
                ) RETURNING id, ingested_at, created_at;
                """,
                (record_id, snapshot_id, acquired_time, raw_hash),
            )
            row = cur.fetchone()
            assert row is not None
            det_id, ingested_at, created_at = row
            assert isinstance(det_id, uuid.UUID)
            assert ingested_at.tzinfo is not None
            assert created_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_populated_detection_with_units(self) -> None:
        """TEST 3: Insert detection with all physical measurements in explicit units."""
        raw_hash = "c" * 64
        acquired_time = datetime(2026, 8, 29, 12, 30, 45, tzinfo=UTC)

        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, record_id = _create_test_lineage(cur)

            cur.execute(
                """
                INSERT INTO detections (
                    source_record_id, source_snapshot_id, source,
                    satellite, instrument, product_type, product_version,
                    acquired_at, latitude, longitude, geometry,
                    frp_mw, brightness_ti4_k, brightness_ti5_k,
                    confidence_raw, day_night, scan, track,
                    raw_identifier, raw_hash, quality_status
                ) VALUES (
                    %s, %s, 'firms',
                    'Suomi-NPP', 'VIIRS', 'standard', 'v2.0',
                    %s, 28.6139, 77.2090,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326),
                    15.75, 342.85, 295.10,
                    'nominal', 'N', 0.38, 0.36,
                    'VIIRS-NPP-20260829-9988', %s, 'valid'
                ) RETURNING id, frp_mw, brightness_ti4_k, brightness_ti5_k,
                            confidence_raw, day_night, scan, track, quality_status;
                """,
                (record_id, snapshot_id, acquired_time, raw_hash),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == 15.75
            assert row[2] == 342.85
            assert row[3] == 295.10
            assert row[4] == "nominal"
            assert row[5] == "N"
            assert row[6] == 0.38
            assert row[7] == 0.36
            assert row[8] == "valid"
            conn.rollback()

    def test_foreign_key_to_source_records_rejected_if_nonexistent(self) -> None:
        """TEST 4: Non-existent source_record_id is rejected by foreign key constraint."""
        non_existent_rec_id = uuid.uuid4()
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, _ = _create_test_lineage(cur)
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO detections (
                        source_record_id, source_snapshot_id, source,
                        satellite, instrument, product_type, product_version,
                        acquired_at, latitude, longitude, geometry, raw_hash
                    ) VALUES (
                        %s, %s, 'firms',
                        'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                        now(), 28.0, 77.0,
                        ST_SetSRID(ST_MakePoint(77.0, 28.0), 4326), %s
                    );
                    """,
                    (non_existent_rec_id, snapshot_id, "d" * 64),
                )
            conn.rollback()

    def test_foreign_key_to_source_snapshots_rejected_if_nonexistent(self) -> None:
        """TEST 5: Non-existent source_snapshot_id is rejected by foreign key constraint."""
        non_existent_snap_id = uuid.uuid4()
        with _get_connection() as conn, conn.cursor() as cur:
            _, _, record_id = _create_test_lineage(cur)
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO detections (
                        source_record_id, source_snapshot_id, source,
                        satellite, instrument, product_type, product_version,
                        acquired_at, latitude, longitude, geometry, raw_hash
                    ) VALUES (
                        %s, %s, 'firms',
                        'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                        now(), 28.0, 77.0,
                        ST_SetSRID(ST_MakePoint(77.0, 28.0), 4326), %s
                    );
                    """,
                    (record_id, non_existent_snap_id, "e" * 64),
                )
            conn.rollback()

    def test_foreign_key_on_delete_restrict_blocks_record_deletion(self) -> None:
        """TEST 6: Deleting parent source_record or snapshot is blocked (RESTRICT)."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, record_id = _create_test_lineage(cur)

            # Insert child detection
            cur.execute(
                """
                INSERT INTO detections (
                    source_record_id, source_snapshot_id, source,
                    satellite, instrument, product_type, product_version,
                    acquired_at, latitude, longitude, geometry, raw_hash
                ) VALUES (
                    %s, %s, 'firms',
                    'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                    now(), 28.0, 77.0,
                    ST_SetSRID(ST_MakePoint(77.0, 28.0), 4326), %s
                );
                """,
                (record_id, snapshot_id, "f" * 64),
            )

            # Deleting parent source_record MUST fail with ForeignKeyViolation
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    "DELETE FROM source_records WHERE id = %s;",
                    (record_id,),
                )
            conn.rollback()

    def test_coordinate_and_geometry_consistency(self) -> None:
        """TEST 7: Validate latitude, longitude, and ST_AsText geometry alignment."""
        lon = 77.2090
        lat = 28.6139
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, record_id = _create_test_lineage(cur)

            cur.execute(
                """
                INSERT INTO detections (
                    source_record_id, source_snapshot_id, source,
                    satellite, instrument, product_type, product_version,
                    acquired_at, latitude, longitude, geometry, raw_hash
                ) VALUES (
                    %s, %s, 'firms',
                    'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                    now(), %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s
                ) RETURNING latitude, longitude, ST_AsText(geometry), ST_SRID(geometry);
                """,
                (record_id, snapshot_id, lat, lon, lon, lat, "1" * 64),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == lat
            assert row[1] == lon
            assert row[2] == f"POINT({lon} {lat})"
            assert row[3] == 4326
            conn.rollback()

    def test_scientific_check_constraints(self) -> None:
        """TEST 8: Verify mathematical bounds on coordinates, temperatures, FRP, scan/track."""
        base_values: dict[str, Any] = {
            "latitude": 28.0,
            "longitude": 77.0,
            "frp_mw": None,
            "brightness_ti4_k": None,
            "brightness_ti5_k": None,
            "scan": None,
            "track": None,
            "day_night": None,
        }

        invalid_cases = [
            ("latitude", 95.0),
            ("latitude", -95.0),
            ("longitude", 185.0),
            ("longitude", -185.0),
            ("frp_mw", -1.0),
            ("brightness_ti4_k", -5.0),
            ("brightness_ti5_k", -10.0),
            ("scan", 0.0),
            ("track", -0.5),
            ("day_night", "X"),
        ]

        for col, val in invalid_cases:
            values = dict(base_values)
            values[col] = val
            with _get_connection() as conn, conn.cursor() as cur:
                _, snapshot_id, record_id = _create_test_lineage(cur)
                with pytest.raises(CheckViolation):
                    cur.execute(
                        """
                        INSERT INTO detections (
                            source_record_id, source_snapshot_id, source,
                            satellite, instrument, product_type, product_version,
                            acquired_at, latitude, longitude, geometry, raw_hash,
                            frp_mw, brightness_ti4_k, brightness_ti5_k,
                            scan, track, day_night
                        ) VALUES (
                            %s, %s, 'firms',
                            'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                            now(), %s, %s,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s,
                            %s, %s, %s,
                            %s, %s, %s
                        );
                        """,
                        (
                            record_id,
                            snapshot_id,
                            values["latitude"],
                            values["longitude"],
                            values["longitude"],
                            values["latitude"],
                            "2" * 64,
                            values["frp_mw"],
                            values["brightness_ti4_k"],
                            values["brightness_ti5_k"],
                            values["scan"],
                            values["track"],
                            values["day_night"],
                        ),
                    )
                conn.rollback()

    def test_raw_hash_length_constraint(self) -> None:
        """TEST 9: Hashes not equal to 64 characters are rejected."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, snapshot_id, record_id = _create_test_lineage(cur)

            # Short hash (63 chars)
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO detections (
                        source_record_id, source_snapshot_id, source,
                        satellite, instrument, product_type, product_version,
                        acquired_at, latitude, longitude, geometry, raw_hash
                    ) VALUES (
                        %s, %s, 'firms',
                        'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                        now(), 28.0, 77.0,
                        ST_SetSRID(ST_MakePoint(77.0, 28.0), 4326), %s
                    );
                    """,
                    (record_id, snapshot_id, "3" * 63),
                )
            conn.rollback()

    def test_full_4_tier_provenance_chain(self) -> None:
        """TEST 10: Validate queryable 4-tier lineage: source -> snapshot -> record -> detection."""
        raw_hash = "4" * 64
        acquired_time = datetime(2026, 8, 29, 14, 20, 0, tzinfo=UTC)

        with _get_connection() as conn, conn.cursor() as cur:
            source_id, snapshot_id, record_id = _create_test_lineage(cur)

            # Insert detection
            cur.execute(
                """
                INSERT INTO detections (
                    source_record_id, source_snapshot_id, source,
                    satellite, instrument, product_type, product_version,
                    acquired_at, latitude, longitude, geometry,
                    frp_mw, brightness_ti4_k, raw_hash
                ) VALUES (
                    %s, %s, 'firms',
                    'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
                    %s, 28.6139, 77.2090,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326),
                    25.5, 355.2, %s
                ) RETURNING id;
                """,
                (record_id, snapshot_id, acquired_time, raw_hash),
            )
            det_id = cur.fetchone()[0]  # type: ignore[index]

            # Execute 4-tier joined lineage query
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
                    det.id AS detection_id,
                    det.satellite,
                    det.instrument,
                    det.frp_mw,
                    det.brightness_ti4_k,
                    ST_AsText(det.geometry) AS det_geom_wkt
                FROM detections det
                JOIN source_records rec ON det.source_record_id = rec.id
                JOIN source_snapshots ss ON det.source_snapshot_id = ss.id
                JOIN source_registry sr ON ss.source_id = sr.id
                WHERE det.id = %s;
                """,
                (det_id,),
            )
            row = cur.fetchone()
            assert row is not None

            # Assert 4-tier lineage integrity
            assert row[0].startswith("test-src-")
            assert row[1] == "NASA FIRMS"
            assert row[2] == "OBSERVATION"
            assert row[3] == snapshot_id
            assert row[4] == "2026.08.29"
            assert row[5] == "AVAILABLE"
            assert row[6] == record_id
            assert row[7] == "RAW-REC-001"
            assert row[9] == det_id
            assert row[10] == "NOAA-20"
            assert row[11] == "VIIRS"
            assert row[12] == 25.5
            assert row[13] == 355.2
            assert row[14] == "POINT(77.209 28.6139)"

            conn.rollback()
