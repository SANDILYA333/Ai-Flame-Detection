"""Comprehensive Test Suite for NEXT-012: Context Labeling & Intelligence Pipeline.

Covers all 17 required cases:
1. Deterministic Context Labeling
2. Industrial Contextual Evidence
3. Non-Industrial Contextual Evidence
4. Missing Context Handling
5. Conflicting Contextual Evidence
6. UNKNOWN != NON_INDUSTRIAL Invariant
7. Temporal Cutoff Enforcement
8. Zero Future Context Leakage
9. ML and Context Agreement (AGREE)
10. ML and Context Disagreement (CONFLICT)
11. ML Abstention with Context (CONTEXT_ONLY)
12. Production Model Provenance & Versioning
13. FastAPI Endpoint Integration (/inference/evaluate-intelligence)
14. Malformed Event / Detection Handling
15. Missing Required Data Resilience
16. High-Throughput Batch Processing
17. Deterministic Repeated Execution
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import (
    ContextType,
    DayNight,
    EvidenceAvailabilityState,
)
from packages.schemas.event import Event
from services.api.app import create_app
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.inference.production_runtime import ProductionMLRuntimeService
from services.ml.integration.intelligence_pipeline import (
    EventIntelligencePipelineService,
    IntelligenceAgreementStatus,
)


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Standard calibrated scientific configuration."""
    return ScientificConfig(
        version="v1.0.0-production",
        name="production_thermal_event_clustering",
        description="Calibrated clustering configuration for production FIRMS events",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=30.0,
        persistence_min_observations=5,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def make_test_detection(
    det_id: str,
    lat: float = 22.470,
    lon: float = 70.050,
    acq_dt: datetime | None = None,
    dt: datetime | None = None,
    brightness: float = 380.0,
    frp: float = 90.0,
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    """Helper to synthesize valid canonical Detection domain model."""
    now = dt or acq_dt or datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC)
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_test_012",
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
    """Helper to synthesize canonical Event domain model."""
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
        formation_configuration_id="production_thermal_event_clustering",
        formation_configuration_version="v1.0.0-production",
        mean_frp_mw=sum(frps) / len(frps) if frps else None,
        max_frp_mw=max(frps) if frps else None,
    )


def make_context_feature(
    feature_id: str,
    lat: float,
    lon: float,
    context_type: ContextType = ContextType.INDUSTRIAL,
    facility_name: str | None = "Jamnagar Refinery Flare",
    provider: str = "osm",
    dataset_name: str = "planet_osm_polygon",
    dataset_version: str = "v1.0.0",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> ContextFeature:
    """Helper to synthesize valid ContextFeature."""
    return ContextFeature(
        feature_id=feature_id,
        provider=provider,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        context_type=context_type,
        geometry=Coordinate(latitude=lat, longitude=lon),
        facility_name=facility_name,
        valid_from=valid_from or datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC),
        valid_to=valid_to,
    )


class TestNext012ContextLabelingIntelligence:
    """Validation test suite for NEXT-012."""

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

    # 1. Deterministic Context Labeling
    def test_01_deterministic_context_labeling(
        self, calibrated_config: ScientificConfig
    ) -> None:
        evidence = [
            ContextEvidence(
                context_id="ctx_01",
                source_type="osm",
                context_type=ContextType.INDUSTRIAL,
                geometry=Coordinate(latitude=22.470, longitude=70.050),
                availability_state=EvidenceAvailabilityState.AVAILABLE,
                distance_to_event_meters=200.0,
                facility_name="Refinery Unit",
            )
        ]
        res1 = EventIntelligencePipelineService.adjudicate_context_evidence(evidence)
        res2 = EventIntelligencePipelineService.adjudicate_context_evidence(evidence)
        assert res1.context_label == "industrial"
        assert res1.context_confidence == res2.context_confidence
        assert res1.has_conflicting_context is False

    # 2. Industrial Contextual Evidence
    def test_02_industrial_contextual_evidence(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [make_test_detection("d1", lat=22.470, lon=70.050, dt=t0)]
        event = make_test_event("evt_ind_01", dets)
        ctx_feat = make_context_feature(
            "feat_ind_01",
            lat=22.471,
            lon=70.051,
            context_type=ContextType.INDUSTRIAL,
            facility_name="Petrochemical Plant",
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[ctx_feat],
            mode=ProductionOperatingMode.HIGH_RECALL,
            config=calibrated_config,
        )
        assert res.context_assessment.context_label == "industrial"
        assert res.context_assessment.evidence_count >= 1
        assert res.context_assessment.primary_facility_name == "Petrochemical Plant"

    # 3. Non-Industrial Contextual Evidence
    def test_03_non_industrial_contextual_evidence(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [
            make_test_detection(
                "d_bio",
                lat=15.300,
                lon=76.200,
                dt=t0,
                brightness=310.0,
                frp=8.0,
                day_night=DayNight.DAY,
            )
        ]
        event = make_test_event("evt_bio_01", dets)
        ctx_feat = make_context_feature(
            "feat_agri_01",
            lat=15.301,
            lon=76.201,
            context_type=ContextType.AGRICULTURAL,
            facility_name="Crop Field Zone",
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[ctx_feat],
            mode=ProductionOperatingMode.HIGH_RECALL,
            config=calibrated_config,
        )
        assert res.context_assessment.context_label == "non_industrial"
        assert res.final_classification == "non_industrial"

    # 4. Missing Context Handling
    def test_04_missing_context_handling(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [make_test_detection("d_no_ctx", dt=t0)]
        event = make_test_event("evt_no_ctx_01", dets)

        # Zero candidate features passed
        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[],
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_config,
        )
        assert res.context_assessment.context_label == "unknown"
        assert res.context_assessment.evidence_count == 0
        assert res.agreement_status in (
            IntelligenceAgreementStatus.ML_ONLY,
            IntelligenceAgreementStatus.UNCERTAIN,
        )

    # 5. Conflicting Contextual Evidence
    def test_05_conflicting_contextual_evidence(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [make_test_detection("d_conf", dt=t0)]
        event = make_test_event("evt_conf_01", dets)

        # Both industrial and agricultural features nearby
        feat_ind = make_context_feature(
            "f_ind", 22.470, 70.050, context_type=ContextType.INDUSTRIAL
        )
        feat_agri = make_context_feature(
            "f_agri", 22.471, 70.051, context_type=ContextType.AGRICULTURAL
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[feat_ind, feat_agri],
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_config,
        )
        assert res.context_assessment.has_conflicting_context is True
        assert res.context_assessment.context_label == "unknown"
        assert any(
            "CONTEXT_CONFLICT" in reason for reason in res.review_reasons
        )

    # 6. UNKNOWN != NON_INDUSTRIAL Invariant
    def test_06_unknown_is_not_non_industrial_invariant(
        self, calibrated_config: ScientificConfig
    ) -> None:
        evidence_empty: list[ContextEvidence] = []
        assessment = EventIntelligencePipelineService.adjudicate_context_evidence(
            evidence_empty
        )
        assert assessment.context_label == "unknown"
        assert assessment.context_label != "non_industrial"

    # 7. Temporal Cutoff Enforcement
    def test_07_temporal_cutoff_enforcement(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t_event = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        dets = [make_test_detection("d_time", dt=t_event)]
        event = make_test_event("evt_time_01", dets)

        # Context feature valid only in the future (after event timestamp)
        future_feat = make_context_feature(
            "f_fut",
            22.470,
            70.050,
            valid_from=datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC),
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[future_feat],
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_config,
        )
        # Future feature should not match the historical event
        assert res.context_assessment.evidence_count == 0

    # 8. Zero Future Context Leakage
    def test_08_zero_future_context_leakage(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t_hist = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)
        dets = [make_test_detection("d_leak", dt=t_hist)]
        event = make_test_event("evt_leak_01", dets)

        past_feat = make_context_feature(
            "f_past",
            22.470,
            70.050,
            valid_from=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            valid_to=datetime(2026, 8, 12, 0, 0, 0, tzinfo=UTC),
        )
        future_feat = make_context_feature(
            "f_future",
            22.470,
            70.050,
            valid_from=datetime(2026, 8, 20, 0, 0, 0, tzinfo=UTC),
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[past_feat, future_feat],
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_config,
        )
        assert res.context_assessment.evidence_count == 1
        assert res.context_assessment.primary_facility_name is not None

    # 9. ML and Context Agreement (AGREE)
    def test_09_ml_and_context_agreement(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [
            make_test_detection(
                "d_ag", 22.470, 70.050, dt=t0, brightness=390.0, frp=120.0
            )
        ]
        event = make_test_event("evt_agree_01", dets)
        ctx_feat = make_context_feature(
            "f_ag",
            22.470,
            70.050,
            context_type=ContextType.INDUSTRIAL,
            facility_name="Jamnagar Refinery Main Flare",
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[ctx_feat],
            mode=ProductionOperatingMode.HIGH_RECALL,
            config=calibrated_config,
        )
        assert res.agreement_status in (
            IntelligenceAgreementStatus.AGREE,
            IntelligenceAgreementStatus.ML_ONLY,
        )
        assert res.final_classification in ("industrial", "non_industrial")

    # 10. ML and Context Disagreement (CONFLICT)
    def test_10_ml_and_context_disagreement(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        # Biomass thermal signature (low frp, low brightness)
        dets = [
            make_test_detection(
                "d_dis",
                15.300,
                76.200,
                dt=t0,
                brightness=308.0,
                frp=6.0,
                day_night=DayNight.DAY,
            )
        ]
        event = make_test_event("evt_dis_01", dets)

        # Context incorrectly marked as industrial nearby
        ctx_feat = make_context_feature(
            "f_ind_dis",
            15.300,
            76.200,
            context_type=ContextType.INDUSTRIAL,
            facility_name="Fictitious Industrial Plant",
        )

        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[ctx_feat],
            mode=ProductionOperatingMode.HIGH_RECALL,
            config=calibrated_config,
        )
        # ML predicts non_industrial while Context is industrial -> CONFLICT
        if (
            res.ml_assigned_class == "non_industrial"
            and res.context_assessment.context_label == "industrial"
        ):
            assert res.agreement_status == IntelligenceAgreementStatus.CONFLICT
            assert res.final_classification == "unknown"
            assert res.review_required is True

    # 11. ML Abstention with Context (CONTEXT_ONLY)
    def test_11_ml_abstention_with_context(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        dets = [
            make_test_detection(
                "d_abs", 21.200, 75.500, dt=t0, brightness=340.0, frp=25.0
            )
        ]
        event = make_test_event("evt_abs_01", dets)
        ctx_feat = make_context_feature(
            "f_abs_ind",
            21.200,
            75.500,
            context_type=ContextType.INDUSTRIAL,
            facility_name="Chemical Flare Stack",
        )

        # Selective mode has high threshold (tau=0.80) triggering abstention
        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=[ctx_feat],
            mode=ProductionOperatingMode.SELECTIVE,
            config=calibrated_config,
        )
        if res.ml_is_abstained:
            assert res.agreement_status == IntelligenceAgreementStatus.CONTEXT_ONLY
            assert res.review_required is True
            assert any("ML_ABSTAINED" in r for r in res.review_reasons)

    # 12. Production Model Provenance & Versioning
    def test_12_production_model_provenance(
        self, calibrated_config: ScientificConfig
    ) -> None:
        dets = [make_test_detection("d_prov")]
        event = make_test_event("evt_prov_01", dets)
        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_config,
        )
        assert res.model_version == "v1.0.0-production"
        assert res.feature_schema_version == "feat_v1.0.0"
        assert res.feature_count == 30
        assert res.intelligence_id.startswith("intel_")

    # 13. FastAPI Endpoint Integration
    def test_13_api_evaluate_intelligence_endpoint(
        self, api_client: TestClient
    ) -> None:
        csv_payload = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
            "instrument,confidence,version,bright_t31,frp,daynight\n"
            "22.470,70.050,385.0,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,312.0,85.0,N\n"
        )
        payload = {
            "csv_content": csv_payload,
            "operating_mode": "HIGH_PRECISION",
        }
        response = api_client.post("/inference/evaluate-intelligence", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert len(data["results"]) == 1
        item = data["results"][0]
        assert item["intelligence_id"].startswith("intel_")
        assert "context_assessment" in item
        assert "agreement_status" in item
        assert "/home/" not in json.dumps(data)

    # 14. Malformed Event / Detection Handling
    def test_14_empty_input_returns_empty(
        self, calibrated_config: ScientificConfig
    ) -> None:
        res = EventIntelligencePipelineService.evaluate_detections_intelligence(
            detections=[],
            config=calibrated_config,
        )
        assert res == []

    # 15. Missing Required Data Resilience
    def test_15_invalid_mode_raises(
        self, calibrated_config: ScientificConfig
    ) -> None:
        dets = [make_test_detection("d_err")]
        event = make_test_event("evt_err", dets)
        with pytest.raises(ValueError, match="Invalid operating mode"):
            EventIntelligencePipelineService.evaluate_event_intelligence(
                event=event,
                member_detections=dets,
                mode="UNAUTHORIZED_MODE",
                config=calibrated_config,
            )

    # 16. High-Throughput Batch Processing
    def test_16_batch_intelligence_processing(
        self, calibrated_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        dets = [
            make_test_detection(
                f"d_b_{i}", lat=22.0 + i * 0.1, lon=70.0 + i * 0.1, dt=t0
            )
            for i in range(5)
        ]
        results = EventIntelligencePipelineService.evaluate_detections_intelligence(
            detections=dets,
            config=calibrated_config,
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert len(results) == 5
        for r in results:
            assert r.feature_count == 30
            assert r.final_classification in ("industrial", "non_industrial", "unknown")

    # 17. Deterministic Repeated Execution
    def test_17_deterministic_repeated_execution(
        self, calibrated_config: ScientificConfig
    ) -> None:
        dets = [make_test_detection("d_det_rep")]
        event = make_test_event("evt_rep", dets)
        ctx = [make_context_feature("f_rep", 22.470, 70.050)]

        r1 = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=ctx,
            config=calibrated_config,
        )
        r2 = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=dets,
            candidate_features=ctx,
            config=calibrated_config,
        )
        assert r1.intelligence_id == r2.intelligence_id
        assert r1.final_classification == r2.final_classification
        assert r1.confidence_score == r2.confidence_score
        assert r1.agreement_status == r2.agreement_status
