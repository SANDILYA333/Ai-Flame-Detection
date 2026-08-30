"""Formal unit/integration tests for ML-012 Real Contextual Enrichment & Labeling.

Validates:
- Context enrichment across external sources (OSM, WRI, GEM, LandCover).
- Reference evidence synthesis with quality tiering and circularity provenance.
- Deterministic label adjudication with Missing != Negative enforcement.
- Strict point-in-time temporal integrity (zero future context leakage).
- End-to-end integration: ML-010 detections -> ML-011 events -> ML-012 labels.
- Serialization, canonical dataset hash integrity, and tamper detection.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight
from packages.schemas.event import Event, RealEnrichedEventDataset
from packages.schemas.ml import (
    LabelConflictPolicy,
    LabelTier,
    ReferenceEvidence,
)


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing a complete, calibrated ScientificConfig for testing."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=10.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


@pytest.fixture
def sample_context_features() -> list[ContextFeature]:
    """Fixture providing standard contextual features for testing."""
    return [
        ContextFeature(
            feature_id="osm_refinery_01",
            provider="osm",
            dataset_name="planet_osm_polygon",
            dataset_version="2026-08-01",
            context_type=ContextType.INDUSTRIAL,
            geometry=Coordinate(latitude=22.4500, longitude=70.0500),
            facility_name="Jamnagar Test Refinery",
            valid_from=datetime(2000, 1, 1, tzinfo=UTC),
        ),
        ContextFeature(
            feature_id="lc_cropland_01",
            provider="landcover",
            dataset_name="dynamic_world",
            dataset_version="2026-08-01",
            context_type=ContextType.AGRICULTURAL,
            geometry=Coordinate(latitude=22.5800, longitude=70.2000),
            facility_name="Kutch Agricultural Zone",
            valid_from=datetime(2015, 1, 1, tzinfo=UTC),
        ),
        ContextFeature(
            feature_id="osm_future_plant_01",
            provider="osm",
            dataset_name="planet_osm_polygon",
            dataset_version="2026-08-01",
            context_type=ContextType.INDUSTRIAL,
            geometry=Coordinate(latitude=22.4500, longitude=70.0500),
            facility_name="Future Hydrogen Plant",
            valid_from=datetime(2026, 12, 1, tzinfo=UTC),
        ),
    ]


def _make_event(
    ev_id: str,
    lat: float,
    lon: float,
    started_at: datetime,
) -> Event:
    """Helper to construct a valid Event domain model."""
    return Event(
        event_id=ev_id,
        detection_ids=[f"det_{ev_id}_1"],
        detection_count=1,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=15),
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="test_profile",
        formation_configuration_version="v1.0-test",
    )


class TestML012ContextLabeling:
    """Comprehensive test suite for ML-012 contextual enrichment & reference labels."""

    def test_context_enrichment_and_facility_matching(
        self,
        calibrated_config: ScientificConfig,
        sample_context_features: list[ContextFeature],
    ) -> None:
        """Event near refinery matches refinery; event in cropland matches cropland."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)

        # Event 1: At Jamnagar refinery centroid (0m distance)
        ev1 = _make_event("ev_industrial", 22.4500, 70.0500, t0)

        # Event 2: In agricultural zone (0m distance)
        ev2 = _make_event("ev_agricultural", 22.5800, 70.2000, t0)

        # Event 3: Isolated offshore location (> 50 km from any feature)
        ev3 = _make_event("ev_isolated", 22.1000, 69.1000, t0)

        det_ds = RealEventConstructionService.construct_events_and_sources(
            detections=[
                Detection(
                    detection_id="d1",
                    source="firms",
                    source_snapshot_id="s1",
                    acquired_at=t0,
                    geometry=Coordinate(latitude=22.4500, longitude=70.0500),
                    satellite="Suomi-NPP",
                    instrument="VIIRS",
                    product_type="nrt",
                    product_version="v2.0",
                    raw_hash="h1",
                    day_night=DayNight.DAY,
                )
            ],
            config=calibrated_config,
        )
        test_event_ds = det_ds.model_copy(
            update={"events": [ev1, ev2, ev3], "event_count": 3}
        )

        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=test_event_ds,
            candidate_features=sample_context_features,
            config=calibrated_config,
        )

        assert len(enriched_ds.reference_labels) == 3

        # Check industrial label
        label_ind = next(
            lbl
            for lbl in enriched_ds.reference_labels
            if lbl.entity_id == "ev_industrial"
        )
        assert label_ind.assigned_class == "industrial"
        assert label_ind.label_tier == LabelTier.TIER_B_STRONG_EVIDENCE
        assert label_ind.is_train_eligible is True

        # Check agricultural label
        label_agri = next(
            lbl
            for lbl in enriched_ds.reference_labels
            if lbl.entity_id == "ev_agricultural"
        )
        assert label_agri.assigned_class == "non_industrial"
        assert label_agri.label_tier == LabelTier.TIER_C_PROXY_WEAK

        # Check isolated event: Zero matched evidence -> "unknown" (Missing != Negative)
        label_iso = next(
            lbl
            for lbl in enriched_ds.reference_labels
            if lbl.entity_id == "ev_isolated"
        )
        assert label_iso.assigned_class == "unknown"
        assert label_iso.label_tier == LabelTier.UNKNOWN
        assert label_iso.is_train_eligible is False

    def test_conflicting_evidence_adjudication(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Conflicting equal-tier claims resolve to unknown with conflict flag."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = _make_event("ev_conflict", 22.5000, 70.1000, t0)

        # Equal-tier conflicting evidence
        ref_ind = ReferenceEvidence(
            evidence_id="ref_ind_01",
            source_name="OSM",
            entity_id="ev_conflict",
            geometry=Coordinate(latitude=22.5000, longitude=70.1000),
            claim_class="industrial",
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            confidence_score=0.85,
        )
        ref_non_ind = ReferenceEvidence(
            evidence_id="ref_non_ind_01",
            source_name="FIELD_SURVEY",
            entity_id="ev_conflict",
            geometry=Coordinate(latitude=22.5000, longitude=70.1000),
            claim_class="non_industrial",
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            confidence_score=0.85,
        )

        decisions = RealContextLabelingService.adjudicate_labels(
            events=[ev],
            reference_evidence=[ref_ind, ref_non_ind],
            conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE,
        )

        assert len(decisions) == 1
        dec = decisions[0]
        assert dec.assigned_class == "unknown"
        assert dec.has_conflicting_evidence is True
        assert dec.is_train_eligible is False

    def test_point_in_time_future_context_rejection(
        self,
        calibrated_config: ScientificConfig,
        sample_context_features: list[ContextFeature],
    ) -> None:
        """Future facility records (valid_from > as_of) are strictly excluded."""
        # Query point-in-time state as of Aug 1 2026
        as_of = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
        ev = _make_event("ev_aug1", 22.4500, 70.0500, as_of - timedelta(hours=2))

        det_ds = RealEventConstructionService.construct_events_and_sources(
            detections=[],
            config=calibrated_config,
        )
        event_ds = det_ds.model_copy(update={"events": [ev], "event_count": 1})

        # Run point-in-time enrichment
        pit_ds = RealContextLabelingService.enrich_and_adjudicate_point_in_time(
            event_dataset=event_ds,
            as_of_time=as_of,
            candidate_features=sample_context_features,
            config=calibrated_config,
        )

        # Future facility 'osm_future_plant_01' (Dec 2026) must NOT appear in evidence
        matched_feature_ids = [
            c.external_facility_id
            for c in pit_ds.context_evidence
            if c.external_facility_id is not None
        ]
        assert "osm_future_plant_01" not in matched_feature_ids

    def test_circularity_audit_and_evidence_payload(
        self,
        calibrated_config: ScientificConfig,
        sample_context_features: list[ContextFeature],
    ) -> None:
        """Reference evidence payloads record matched context ID and facility."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = _make_event("ev_circ", 22.4500, 70.0500, t0)

        det_ds = RealEventConstructionService.construct_events_and_sources(
            detections=[],
            config=calibrated_config,
        )
        event_ds = det_ds.model_copy(update={"events": [ev], "event_count": 1})

        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=event_ds,
            candidate_features=sample_context_features,
            config=calibrated_config,
        )

        assert len(enriched_ds.reference_evidence) >= 1
        ref = enriched_ds.reference_evidence[0]
        assert "contributing_context_id" in ref.evidence_payload
        assert "facility_name" in ref.evidence_payload
        assert "distance_meters" in ref.evidence_payload
        assert ref.evidence_payload["facility_name"] == "Jamnagar Test Refinery"

    def test_end_to_end_pipeline_from_ml010_to_ml012(
        self,
        calibrated_config: ScientificConfig,
    ) -> None:
        """Real fixture traverses ML-010 -> ML-011 -> ML-012 with provenance."""
        # 1. Ingest ML-010 detections
        fixture_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
        detection_ds = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )

        # 2. Derive ML-011 events
        event_ds = RealEventConstructionService.construct_events_and_sources(
            detection_dataset=detection_ds,
            config=calibrated_config,
        )

        # 3. Load ML-012 context fixture
        ctx_fixture_path = Path("fixtures/context/context_sample_jamnagar.json")
        features, hashes = (
            RealContextLabelingService.load_context_features_from_fixture(
                ctx_fixture_path
            )
        )

        # 4. Derive ML-012 enriched dataset
        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=event_ds,
            candidate_features=features,
            snapshot_hashes=hashes,
            config=calibrated_config,
            data_status="OFFLINE_FIXTURE",
        )

        assert isinstance(enriched_ds, RealEnrichedEventDataset)
        assert len(enriched_ds.events) == event_ds.event_count
        assert len(enriched_ds.reference_labels) == event_ds.event_count
        assert enriched_ds.source_event_dataset_hash == event_ds.canonical_dataset_hash
        assert (
            enriched_ds.source_detection_dataset_hash
            == detection_ds.manifest.canonical_dataset_hash
        )

    def test_save_and_load_with_tamper_detection(
        self,
        calibrated_config: ScientificConfig,
        sample_context_features: list[ContextFeature],
    ) -> None:
        """Enriched dataset serializes cleanly and detects tampered labels."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = _make_event("ev_save", 22.4500, 70.0500, t0)

        det_ds = RealEventConstructionService.construct_events_and_sources(
            detections=[],
            config=calibrated_config,
        )
        event_ds = det_ds.model_copy(update={"events": [ev], "event_count": 1})

        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=event_ds,
            candidate_features=sample_context_features,
            config=calibrated_config,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = RealContextLabelingService.save_dataset(enriched_ds, tmp_dir)
            assert out_path.exists()

            # Clean reload
            reloaded = RealContextLabelingService.load_dataset(out_path)
            assert reloaded.canonical_dataset_hash == enriched_ds.canonical_dataset_hash
            assert len(reloaded.reference_labels) == len(enriched_ds.reference_labels)

            # Tampered reload
            import json

            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["reference_labels"][0]["assigned_class"] = "tampered_class"
            out_path.write_text(json.dumps(data), encoding="utf-8")

            with pytest.raises(
                ValueError, match="Enriched event dataset hash mismatch"
            ):
                RealContextLabelingService.load_dataset(out_path)
