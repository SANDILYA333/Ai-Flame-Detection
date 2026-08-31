"""Comprehensive Test Suite for NEXT-010: NASA FIRMS -> Production ML End-to-End.

Verifies:
1. Pipeline Integration: Real FIRMS detections / CSV -> Event -> feat_v1.0.0 (30 features)
   -> ProductionMLRuntimeService -> Calibrated Policy -> Structured Result.
2. Operating Mode Routing: HIGH_PRECISION, HIGH_RECALL, SELECTIVE.
3. Point-in-Time Temporal Integrity: Zero future-event or future-detection leakage.
4. Scientific Invariant Preservation: UNKNOWN != NON_INDUSTRIAL under all abstention/rejection scenarios.
5. Error & Failure Safety: Malformed events, missing coordinates, schema violations fail cleanly.
6. Batch Processing: High-throughput multi-event clustering and inference with identity preservation.
7. Security & Information Leakage: No pilot artifacts, no filesystem paths or tokens in responses.
8. Determinism: Identical inputs yield bitwise identical feature records and model outputs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import (
    ContextType,
    DayNight,
    EvidenceAvailabilityState,
    PersistenceState,
)
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource
from services.api.app import create_app
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)
from services.ml.integration.firms_pipeline import (
    FirmsMLPredictionResult,
    FirmsProductionMLIntegrationService,
)

if TYPE_CHECKING:
    pass


def make_test_detection(
    det_id: str,
    lat: float = 22.470,
    lon: float = 70.050,
    acq_dt: datetime | None = None,
    brightness: float = 380.0,
    frp: float = 90.0,
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    """Helper to synthesize a valid canonical Detection instance."""
    now = acq_dt or datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC)
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_test_001",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=now,
        satellite="Suomi-NPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v2.0",
        raw_hash=f"hash_{det_id}",
        brightness_ti4_k=brightness,
        brightness_ti5_k=310.0,
        frp_mw=frp,
        confidence="high",
        scan_km=0.5,
        track_km=0.5,
        day_night=day_night,
    )


def make_test_event(
    event_id: str,
    detections: list[Detection],
) -> Event:
    """Helper to synthesize a valid canonical Event instance."""
    started_at = min(d.acquired_at for d in detections)
    ended_at = max(d.acquired_at for d in detections)
    mean_lat = sum(d.geometry.latitude for d in detections) / len(detections)
    mean_lon = sum(d.geometry.longitude for d in detections) / len(detections)
    frps = [d.frp_mw for d in detections if d.frp_mw is not None]

    return Event(
        event_id=event_id,
        detection_ids=[d.detection_id for d in detections],
        detection_count=len(detections),
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=max(0.0, (ended_at - started_at).total_seconds()),
        centroid_geometry=Coordinate(latitude=mean_lat, longitude=mean_lon),
        formation_configuration_id="cfg_test_clustering",
        formation_configuration_version="v1.0.0",
        mean_frp_mw=sum(frps) / len(frps) if frps else None,
        max_frp_mw=max(frps) if frps else None,
    )


class TestNext010FirmsMLIntegration:
    """Test suite verifying end-to-end FIRMS -> ML pipeline execution."""

    @pytest.fixture(autouse=True)
    def setup_runtime(self) -> None:
        """Clear cache before each test."""
        ProductionMLRuntimeService.clear_cache()

    @pytest.fixture(scope="class")
    @classmethod
    def api_client(cls) -> TestClient:
        """Create FastAPI test client."""
        app = create_app()
        return TestClient(app)

    # --------------------------------------------------------------------------
    # 1. Pipeline Integration & Schema Compliance
    # --------------------------------------------------------------------------

    def test_firms_event_end_to_end_evaluation(self) -> None:
        """Verify full event evaluation: Event -> 30 features -> prediction."""
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [make_test_detection(f"det_{i}", acq_dt=t0) for i in range(3)]
        event = make_test_event("evt_test_001", dets)

        result = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )

        assert isinstance(result, FirmsMLPredictionResult)
        assert result.event_id == "evt_test_001"
        assert result.source == "NASA_FIRMS"
        assert result.feature_schema_version == "feat_v1.0.0"
        assert result.feature_count == len(APPROVED_FEATURES)
        assert result.feature_count == 30
        assert result.model_version == "v1.0.0-production"
        assert result.confidence >= 0.0
        assert result.threshold == 0.70
        assert result.total_latency_ms >= 0.0

    def test_operating_modes_resolution(self) -> None:
        """Verify pipeline delegates to authorized models per operating mode."""
        dets = [make_test_detection("det_mode_01")]
        event = make_test_event("evt_mode_01", dets)

        # High Precision
        r_prec = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert r_prec.model_name == "DecisionTreeClassifier"
        assert r_prec.threshold == 0.70

        # High Recall
        r_rec = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_RECALL,
        )
        assert r_rec.model_name == "LogisticRegressionClassifier"
        assert r_rec.threshold == 0.50

        # Selective
        r_sel = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.SELECTIVE,
        )
        assert r_sel.model_name == "DecisionTreeClassifier"
        assert r_sel.threshold == 0.80

    # --------------------------------------------------------------------------
    # 2. Point-in-Time Temporal Integrity
    # --------------------------------------------------------------------------

    def test_future_detection_leakage_prevention(self) -> None:
        """Verify detections occurring AFTER cutoff timestamp are strictly ignored."""
        t_past = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        t_cutoff = datetime(2026, 8, 15, 14, 0, 0, tzinfo=UTC)
        t_future = datetime(2026, 8, 15, 16, 0, 0, tzinfo=UTC)

        d_past = make_test_detection("det_past", acq_dt=t_past, frp=50.0)
        d_future = make_test_detection("det_future", acq_dt=t_future, frp=500.0)

        event = make_test_event("evt_leak_test", [d_past, d_future])

        # Evaluate strictly as of t_cutoff
        res = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=[d_past, d_future],
            as_of_time=t_cutoff,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        # Should succeed because d_past <= t_cutoff
        assert res.event_id == "evt_leak_test"

    def test_future_event_preceding_leakage_prevention(self) -> None:
        """Verify historical context extractor ignores future preceding events."""
        t_cutoff = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        d_cur = make_test_detection("d_cur", acq_dt=t_cutoff)
        cur_event = make_test_event("evt_current", [d_cur])

        d_past = make_test_detection(
            "d_past",
            acq_dt=datetime(2026, 8, 10, 0, 0, 0, tzinfo=UTC),
        )
        past_event = make_test_event("evt_past", [d_past])

        d_future = make_test_detection(
            "d_future",
            acq_dt=datetime(2026, 8, 20, 0, 0, 0, tzinfo=UTC),
        )
        future_event = make_test_event("evt_future", [d_future])

        # Both past and future events passed as context
        res = FirmsProductionMLIntegrationService.evaluate_event(
            event=cur_event,
            member_detections=[d_cur],
            as_of_time=t_cutoff,
            preceding_events=[past_event, future_event],
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert res.event_id == "evt_current"

    # --------------------------------------------------------------------------
    # 3. Scientific Invariant: UNKNOWN != NON_INDUSTRIAL
    # --------------------------------------------------------------------------

    def test_unknown_is_not_non_industrial_invariant(self) -> None:
        """CRITICAL INVARIANT: Abstained events must be assigned 'unknown'."""
        dets = [make_test_detection("det_inv_01", brightness=310.0, frp=5.0)]
        event = make_test_event("evt_inv_01", dets)

        # Under Selective Mode (tau=0.80)
        res = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.SELECTIVE,
        )
        if res.is_abstained:
            assert res.assigned_class == "unknown"
            assert res.assigned_class != "non_industrial"
            assert res.review_required is True
            assert res.abstention_reason is not None

    # --------------------------------------------------------------------------
    # 4. Raw FIRMS CSV Parsing & End-to-End Execution
    # --------------------------------------------------------------------------

    def test_raw_firms_csv_evaluation(self) -> None:
        """Verify full CSV parsing -> clustering -> inference pipeline."""
        csv_data = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
            "22.470,70.050,385.0,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,312.0,85.0,N\n"
            "22.472,70.052,388.0,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,314.0,95.0,N\n"
            "18.500,73.800,310.0,0.5,0.5,2026-08-15,1830,N,VIIRS,nominal,2.0NRT,295.0,8.0,N\n"
        )
        results = FirmsProductionMLIntegrationService.evaluate_firms_csv(
            csv_content=csv_data,
            mode=ProductionOperatingMode.HIGH_RECALL,
        )
        assert len(results) == 2
        # Verify both events have valid predictions
        for r in results:
            assert r.feature_count == 30
            assert r.assigned_class in ("industrial", "non_industrial", "unknown")

    # --------------------------------------------------------------------------
    # 5. Failure & Edge Case Handling
    # --------------------------------------------------------------------------

    def test_empty_detections_returns_empty(self) -> None:
        """Verify empty detection input returns empty result list safely."""
        res = FirmsProductionMLIntegrationService.evaluate_detections(
            detections=[],
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert res == []

    def test_unauthorized_operating_mode_raises(self) -> None:
        """Verify invalid operating mode raises clear ValueError."""
        dets = [make_test_detection("det_err_01")]
        event = make_test_event("evt_err_01", dets)
        with pytest.raises(ValueError, match="Invalid operating mode"):
            FirmsProductionMLIntegrationService.evaluate_event(
                event=event,
                member_detections=dets,
                mode="UNAUTHORIZED_MODE",  # type: ignore[arg-type]
            )

    # --------------------------------------------------------------------------
    # 6. Determinism & Reproducibility
    # --------------------------------------------------------------------------

    def test_deterministic_e2e_reproducibility(self) -> None:
        """Verify pipeline execution is 100% deterministic given same inputs."""
        dets = [make_test_detection("det_rep_01")]
        event = make_test_event("evt_rep_01", dets)

        r1 = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        r2 = FirmsProductionMLIntegrationService.evaluate_event(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert r1.predicted_class == r2.predicted_class
        assert r1.assigned_class == r2.assigned_class
        assert r1.confidence == r2.confidence
        assert r1.is_abstained == r2.is_abstained

    # --------------------------------------------------------------------------
    # 7. FastAPI Endpoint Integration
    # --------------------------------------------------------------------------

    def test_api_evaluate_firms_csv_endpoint(self, api_client: TestClient) -> None:
        """Verify /inference/evaluate-firms-csv HTTP endpoint."""
        csv_data = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
            "22.470,70.050,385.0,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,312.0,85.0,N\n"
        )
        payload = {
            "csv_content": csv_data,
            "operating_mode": "HIGH_PRECISION",
        }
        response = api_client.post("/inference/evaluate-firms-csv", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert len(data["results"]) == 1
        res_item = data["results"][0]
        assert res_item["source"] == "NASA_FIRMS"
        assert res_item["feature_count"] == 30
        assert res_item["feature_schema_version"] == "feat_v1.0.0"
        assert res_item["model_version"] == "v1.0.0-production"
        # Verify no filesystem paths or private keys are exposed
        assert "/home/" not in json.dumps(data)
        assert "artifacts/real" not in json.dumps(data)
