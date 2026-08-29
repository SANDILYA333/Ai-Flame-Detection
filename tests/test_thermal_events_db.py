"""Integration tests for DB-008 thermal events and detection membership schema."""

import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

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


def _create_test_detection(
    cur: psycopg.Cursor[tuple[Any, ...]],
    lon: float = 77.2090,
    lat: float = 28.6139,
    frp: float = 15.0,
    raw_hash: str | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Helper to create complete upstream lineage: source -> snap -> record -> detection."""
    if raw_hash is None:
        raw_hash = uuid.uuid4().hex + uuid.uuid4().hex

    source_name = f"test-src-{uuid.uuid4().hex[:8]}"
    cur.execute(
        """
        INSERT INTO source_registry (name, provider, source_type, role)
        VALUES (%s, 'NASA FIRMS', 'satellite', %s)
        RETURNING id;
        """,
        (source_name, SourceRole.OBSERVATION.value),
    )
    source_id = cur.fetchone()[0]  # type: ignore[index]

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
    snapshot_id = cur.fetchone()[0]  # type: ignore[index]

    cur.execute(
        """
        INSERT INTO source_records (
            source_snapshot_id, external_record_id, record_hash,
            geometry
        ) VALUES (
            %s, 'RAW-REC-001', %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        ) RETURNING id;
        """,
        (snapshot_id, raw_hash, lon, lat),
    )
    record_id = cur.fetchone()[0]  # type: ignore[index]

    cur.execute(
        """
        INSERT INTO detections (
            source_record_id, source_snapshot_id, source,
            satellite, instrument, product_type, product_version,
            acquired_at, latitude, longitude, geometry,
            frp_mw, raw_hash
        ) VALUES (
            %s, %s, 'firms',
            'NOAA-20', 'VIIRS', 'nrt', 'v1.0',
            now(), %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s
        ) RETURNING id;
        """,
        (record_id, snapshot_id, lat, lon, lon, lat, frp, raw_hash),
    )
    detection_id = cur.fetchone()[0]  # type: ignore[index]

    return source_id, snapshot_id, record_id, detection_id


@pytest.mark.integration
class TestThermalEventsPersistence:
    """Validate thermal_events and event_detections schemas, spatial and temporal invariants."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_thermal_events_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, nullability, defaults, and PostGIS metadata."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "scientific_contract_id": ("uuid", "YES"),
            "formation_run_id": ("character varying", "YES"),
            "formation_status": ("character varying", "NO"),
            "started_at": ("timestamp with time zone", "NO"),
            "ended_at": ("timestamp with time zone", "NO"),
            "duration_seconds": ("double precision", "YES"),
            "detection_count": ("integer", "NO"),
            "centroid_geometry": ("USER-DEFINED", "NO"),
            "observation_geometry": ("USER-DEFINED", "YES"),
            "mean_frp_mw": ("double precision", "YES"),
            "max_frp_mw": ("double precision", "YES"),
            "total_frp_mw": ("double precision", "YES"),
            "metadata_json": ("jsonb", "YES"),
            "created_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'thermal_events';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in thermal_events"
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
                WHERE f_table_name = 'thermal_events'
                ORDER BY f_geometry_column;
                """
            )
            geom_rows = cur.fetchall()
            assert len(geom_rows) == 2

            # centroid_geometry
            assert geom_rows[0][0] == "centroid_geometry"
            assert geom_rows[0][1] == 2
            assert geom_rows[0][2] == 4326
            assert geom_rows[0][3] == "POINT"

            # observation_geometry
            assert geom_rows[1][0] == "observation_geometry"
            assert geom_rows[1][1] == 2
            assert geom_rows[1][2] == 4326
            assert geom_rows[1][3] == "GEOMETRY"

    def test_event_detections_table_structure(self) -> None:
        """TEST 2: Verify event_detections association table schema and uniqueness."""
        expected_columns = {
            "id": ("uuid", "NO"),
            "event_id": ("uuid", "NO"),
            "detection_id": ("uuid", "NO"),
            "membership_confidence": ("double precision", "YES"),
            "metadata_json": ("jsonb", "YES"),
            "created_at": ("timestamp with time zone", "NO"),
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'event_detections';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: (row[1], row[2]) for row in rows}

            for col, (expected_type, expected_null) in expected_columns.items():
                assert col in found, f"Column '{col}' not found in event_detections"
                actual_type, actual_null = found[col]
                assert actual_type == expected_type
                assert actual_null == expected_null

    def test_insert_minimal_valid_event(self) -> None:
        """TEST 3: Insert event with required fields and verify defaults."""
        now = datetime.now(UTC)
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO thermal_events (
                    started_at, ended_at, detection_count, centroid_geometry
                ) VALUES (
                    %s, %s, 1,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326)
                ) RETURNING id, formation_status, created_at;
                """,
                (now, now),
            )
            row = cur.fetchone()
            assert row is not None
            event_id, status, created_at = row
            assert isinstance(event_id, uuid.UUID)
            assert status == "FORMED"
            assert created_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_populated_event_with_units(self) -> None:
        """TEST 4: Insert event with duration, FRP stats (MW), and Polygon geometry."""
        start = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        end = datetime(2026, 8, 29, 11, 30, 0, tzinfo=UTC)
        poly_wkt = (
            "POLYGON((77.1 28.5, 77.3 28.5, 77.3 28.7, 77.1 28.7, 77.1 28.5))"
        )

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO thermal_events (
                    formation_run_id, formation_status,
                    started_at, ended_at, duration_seconds, detection_count,
                    centroid_geometry, observation_geometry,
                    mean_frp_mw, max_frp_mw, total_frp_mw
                ) VALUES (
                    'RUN-20260829-001', 'REFINED',
                    %s, %s, 5400.0, 5,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326),
                    ST_SetSRID(ST_PolygonFromText(%s), 4326),
                    22.5, 45.0, 112.5
                ) RETURNING id, duration_seconds, mean_frp_mw, max_frp_mw, total_frp_mw,
                            ST_GeometryType(observation_geometry);
                """,
                (start, end, poly_wkt),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == 5400.0
            assert row[2] == 22.5
            assert row[3] == 45.0
            assert row[4] == 112.5
            assert row[5] == "ST_Polygon"
            conn.rollback()

    def test_event_detections_membership_and_uniqueness(self) -> None:
        """TEST 5: Associate member detections and enforce composite uniqueness."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, _, _, det_id1 = _create_test_lineage_detection(cur, 77.2, 28.6, 10.0)
            _, _, _, det_id2 = _create_test_lineage_detection(cur, 77.3, 28.7, 20.0)

            # Insert event
            now = datetime.now(UTC)
            cur.execute(
                """
                INSERT INTO thermal_events (
                    started_at, ended_at, detection_count, centroid_geometry
                ) VALUES (
                    %s, %s, 2,
                    ST_SetSRID(ST_MakePoint(77.25, 28.65), 4326)
                ) RETURNING id;
                """,
                (now, now),
            )
            event_id = cur.fetchone()[0]  # type: ignore[index]

            # Insert 2 association rows
            cur.execute(
                """
                INSERT INTO event_detections (event_id, detection_id, membership_confidence)
                VALUES (%s, %s, 0.95), (%s, %s, 0.88);
                """,
                (event_id, det_id1, event_id, det_id2),
            )

            # Attempting duplicate membership must fail with UniqueViolation
            with pytest.raises(UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO event_detections (event_id, detection_id)
                    VALUES (%s, %s);
                    """,
                    (event_id, det_id1),
                )
            conn.rollback()

    def test_foreign_key_on_delete_restrict(self) -> None:
        """TEST 6: Deleting parent detections or thermal_events is blocked (RESTRICT)."""
        with _get_connection() as conn, conn.cursor() as cur:
            _, _, _, det_id = _create_test_lineage_detection(cur, 77.2, 28.6, 15.0)

            now = datetime.now(UTC)
            cur.execute(
                """
                INSERT INTO thermal_events (
                    started_at, ended_at, detection_count, centroid_geometry
                ) VALUES (
                    %s, %s, 1,
                    ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                ) RETURNING id;
                """,
                (now, now),
            )
            event_id = cur.fetchone()[0]  # type: ignore[index]

            cur.execute(
                """
                INSERT INTO event_detections (event_id, detection_id)
                VALUES (%s, %s);
                """,
                (event_id, det_id),
            )

            # Deleting parent thermal_event MUST fail with ForeignKeyViolation
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    "DELETE FROM thermal_events WHERE id = %s;",
                    (event_id,),
                )
            conn.rollback()

        with _get_connection() as conn, conn.cursor() as cur:
            _, _, _, det_id = _create_test_lineage_detection(cur, 77.2, 28.6, 15.0)
            now = datetime.now(UTC)
            cur.execute(
                """
                INSERT INTO thermal_events (
                    started_at, ended_at, detection_count, centroid_geometry
                ) VALUES (
                    %s, %s, 1,
                    ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                ) RETURNING id;
                """,
                (now, now),
            )
            event_id = cur.fetchone()[0]  # type: ignore[index]

            cur.execute(
                """
                INSERT INTO event_detections (event_id, detection_id)
                VALUES (%s, %s);
                """,
                (event_id, det_id),
            )

            # Deleting parent detection MUST fail with ForeignKeyViolation
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    "DELETE FROM detections WHERE id = %s;",
                    (det_id,),
                )
            conn.rollback()

    def test_temporal_check_constraints(self) -> None:
        """TEST 7: Verify ended_at >= started_at and duration_seconds >= 0."""
        start = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
        end_invalid = datetime(2026, 8, 29, 11, 0, 0, tzinfo=UTC)

        # ended_at < started_at must fail
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO thermal_events (
                        started_at, ended_at, detection_count, centroid_geometry
                    ) VALUES (
                        %s, %s, 1,
                        ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                    );
                    """,
                    (start, end_invalid),
                )
            conn.rollback()

        # duration_seconds < 0 must fail
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO thermal_events (
                        started_at, ended_at, duration_seconds, detection_count, centroid_geometry
                    ) VALUES (
                        %s, %s, -10.0, 1,
                        ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                    );
                    """,
                    (start, start),
                )
            conn.rollback()

    def test_detection_count_and_frp_check_constraints(self) -> None:
        """TEST 8: Verify detection_count >= 1 and non-negative FRP stats."""
        now = datetime.now(UTC)

        # detection_count < 1 must fail
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO thermal_events (
                        started_at, ended_at, detection_count, centroid_geometry
                    ) VALUES (
                        %s, %s, 0,
                        ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                    );
                    """,
                    (now, now),
                )
            conn.rollback()

        # mean_frp_mw < 0 must fail
        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO thermal_events (
                        started_at, ended_at, detection_count, centroid_geometry, mean_frp_mw
                    ) VALUES (
                        %s, %s, 1,
                        ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326), -1.0
                    );
                    """,
                    (now, now),
                )
            conn.rollback()

    def test_scientific_contract_foreign_key(self) -> None:
        """TEST 9: Verify optional foreign key to scientific_contracts."""
        non_existent_contract_id = uuid.uuid4()
        now = datetime.now(UTC)

        with _get_connection() as conn, conn.cursor() as cur:
            with pytest.raises(ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO thermal_events (
                        scientific_contract_id, started_at, ended_at,
                        detection_count, centroid_geometry
                    ) VALUES (
                        %s, %s, %s,
                        1, ST_SetSRID(ST_MakePoint(77.2, 28.6), 4326)
                    );
                    """,
                    (non_existent_contract_id, now, now),
                )
            conn.rollback()

    def test_full_5_tier_provenance_chain(self) -> None:
        """TEST 10: Validate 5-tier lineage: source -> snap -> record -> detection -> event."""
        with _get_connection() as conn, conn.cursor() as cur:
            src_id, snap_id, rec_id, det_id = _create_test_lineage_detection(
                cur, 77.2090, 28.6139, 32.5
            )

            now = datetime.now(UTC)
            cur.execute(
                """
                INSERT INTO thermal_events (
                    started_at, ended_at, detection_count, centroid_geometry,
                    mean_frp_mw, max_frp_mw, total_frp_mw
                ) VALUES (
                    %s, %s, 1,
                    ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326),
                    32.5, 32.5, 32.5
                ) RETURNING id;
                """,
                (now, now),
            )
            event_id = cur.fetchone()[0]  # type: ignore[index]

            cur.execute(
                """
                INSERT INTO event_detections (event_id, detection_id, membership_confidence)
                VALUES (%s, %s, 0.99);
                """,
                (event_id, det_id),
            )

            # Execute 5-tier joined lineage query
            cur.execute(
                """
                SELECT
                    sr.name AS source_name,
                    sr.provider AS source_provider,
                    ss.id AS snapshot_id,
                    rec.id AS record_id,
                    det.id AS detection_id,
                    det.satellite,
                    det.frp_mw AS det_frp,
                    ed.membership_confidence,
                    te.id AS event_id,
                    te.detection_count,
                    te.mean_frp_mw AS event_mean_frp,
                    ST_AsText(te.centroid_geometry) AS centroid_wkt
                FROM thermal_events te
                JOIN event_detections ed ON te.id = ed.event_id
                JOIN detections det ON ed.detection_id = det.id
                JOIN source_records rec ON det.source_record_id = rec.id
                JOIN source_snapshots ss ON det.source_snapshot_id = ss.id
                JOIN source_registry sr ON ss.source_id = sr.id
                WHERE te.id = %s;
                """,
                (event_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0].startswith("test-src-")
            assert row[1] == "NASA FIRMS"
            assert row[2] == snap_id
            assert row[3] == rec_id
            assert row[4] == det_id
            assert row[5] == "NOAA-20"
            assert row[6] == 32.5
            assert row[7] == 0.99
            assert row[8] == event_id
            assert row[9] == 1
            assert row[10] == 32.5
            assert row[11] == "POINT(77.209 28.6139)"

            conn.rollback()


def _create_test_lineage_detection(
    cur: psycopg.Cursor[tuple[Any, ...]],
    lon: float,
    lat: float,
    frp: float,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Helper creating full source -> snap -> record -> detection lineage."""
    return _create_test_detection(cur, lon=lon, lat=lat, frp=frp)
