"""Integration tests for DB-003 scientific contracts database schema."""

import json
import os
import shutil
import subprocess
import uuid
from typing import Any

import psycopg
import pytest
from psycopg.errors import CheckViolation, UniqueViolation

from packages.config import get_settings


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
class TestScientificContractsPersistence:
    """Validate scientific_contracts schema, constraints, and data integrity."""

    @pytest.fixture(autouse=True)
    def require_running_db(self) -> None:
        """Skip test if postgres container is offline."""
        if not _is_docker_and_container_available():
            pytest.skip("postgres-postgis container is not running.")

    def test_scientific_contracts_table_structure(self) -> None:
        """TEST 1: Verify columns, data types, and nullability."""
        expected_columns = {
            "id": "uuid",
            "version": "character varying",
            "name": "character varying",
            "description": "text",
            "created_at": "timestamp with time zone",
            "fingerprint": "character varying",
            "spatial_cluster_radius_meters": "double precision",
            "temporal_window_hours": "double precision",
            "persistence_threshold_days": "double precision",
            "persistence_min_observations": "integer",
            "attribution_radius_meters": "double precision",
            "attribution_confidence_threshold": "double precision",
            "minimum_event_confidence": "double precision",
            "abstention_confidence_threshold": "double precision",
            "raw_config": "jsonb",
            "is_active": "boolean",
        }

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'scientific_contracts';
                """
            )
            rows = cur.fetchall()
            found = {row[0]: row[1] for row in rows}
            nullability = {row[0]: row[2] for row in rows}

            for col, dtype in expected_columns.items():
                assert col in found, f"Column '{col}' not found in scientific_contracts"
                assert found[col] == dtype, (
                    f"Column '{col}' type expected {dtype}, got {found[col]}"
                )

            # Verify all 8 scientific parameters are NULLABLE (no forced defaults)
            scientific_params = [
                "spatial_cluster_radius_meters",
                "temporal_window_hours",
                "persistence_threshold_days",
                "persistence_min_observations",
                "attribution_radius_meters",
                "attribution_confidence_threshold",
                "minimum_event_confidence",
                "abstention_confidence_threshold",
            ]
            for param in scientific_params:
                assert nullability[param] == "YES", (
                    f"Parameter '{param}' must be nullable"
                )

    def test_insert_uncalibrated_scientific_contract(self) -> None:
        """TEST 2: Insert uncalibrated contract with all thresholds NULL."""
        version_tag = f"test-uncalibrated-{uuid.uuid4().hex[:8]}"
        fingerprint = "0000000000000000000000000000000000000000000000000000000000000000"

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scientific_contracts (
                    version, name, description, fingerprint,
                    spatial_cluster_radius_meters,
                    temporal_window_hours,
                    persistence_threshold_days,
                    persistence_min_observations,
                    attribution_radius_meters,
                    attribution_confidence_threshold,
                    minimum_event_confidence,
                    abstention_confidence_threshold,
                    is_active
                ) VALUES (
                    %s, %s, %s, %s,
                    NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL, NULL,
                    false
                ) RETURNING id, created_at;
                """,
                (
                    version_tag,
                    "uncalibrated_profile",
                    "draft uncalibrated notes",
                    fingerprint,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            contract_id, created_at = row
            assert isinstance(contract_id, uuid.UUID)
            assert created_at.tzinfo is not None
            conn.rollback()

    def test_insert_fully_calibrated_valid_contract(self) -> None:
        """TEST 3: Insert fully populated valid contract."""
        version_tag = f"v1.0.0-test-{uuid.uuid4().hex[:8]}"
        raw_payload = json.dumps(
            {"version": version_tag, "spatial_cluster_radius_meters": 1500.0}
        )

        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scientific_contracts (
                    version, name, description, fingerprint,
                    spatial_cluster_radius_meters,
                    temporal_window_hours,
                    persistence_threshold_days,
                    persistence_min_observations,
                    attribution_radius_meters,
                    attribution_confidence_threshold,
                    minimum_event_confidence,
                    abstention_confidence_threshold,
                    raw_config,
                    is_active
                ) VALUES (
                    %s, %s, %s, %s,
                    1500.0, 24.0, 30.0, 5,
                    2000.0, 0.85, 0.70, 0.50,
                    %s, true
                ) RETURNING id, spatial_cluster_radius_meters, is_active;
                """,
                (
                    version_tag,
                    "production_baseline",
                    "production calibrated config",
                    "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    raw_payload,
                ),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] == 1500.0
            assert row[2] is True
            conn.rollback()

    def test_version_uniqueness_constraint(self) -> None:
        """TEST 4: Duplicate version strings are rejected by unique constraint."""
        version_tag = f"unique-ver-{uuid.uuid4().hex[:8]}"
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scientific_contracts (version, fingerprint)
                VALUES (%s, 'fingerprint1');
                """,
                (version_tag,),
            )
            with pytest.raises(UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO scientific_contracts (version, fingerprint)
                    VALUES (%s, 'fingerprint2');
                    """,
                    (version_tag,),
                )
            conn.rollback()

    def test_check_constraints_reject_invalid_values(self) -> None:
        """TEST 5: Check constraints reject negative radius and invalid confidence."""
        with _get_connection() as conn, conn.cursor() as cur:
            # Negative radius
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO scientific_contracts (
                        version, fingerprint, spatial_cluster_radius_meters
                    ) VALUES ('v-invalid-radius', 'fp', -100.0);
                    """
                )
            conn.rollback()

        with _get_connection() as conn, conn.cursor() as cur:
            # Probability > 1.0
            with pytest.raises(CheckViolation):
                cur.execute(
                    """
                    INSERT INTO scientific_contracts (
                        version, fingerprint, attribution_confidence_threshold
                    ) VALUES ('v-invalid-conf', 'fp', 1.2);
                    """
                )
            conn.rollback()
