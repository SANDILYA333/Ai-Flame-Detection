"""Formal unit/integration tests for ML-011 Event Construction & Source Tracking.

Validates:
- Spatiotemporal clustering correctness (spatial radius, temporal window).
- Deterministic event ID and source ID generation.
- Strict point-in-time temporal integrity (zero future detection/event leakage).
- Persistent thermal source tracking (association, active days, recurrence).
- Complete provenance linkage (source -> events -> detections).
- Anti-leakage invariants (zero dependency on facility IDs, labels, or future).
- End-to-end pipeline execution from ML-010 real NASA FIRMS fixture.
- Save/load serialization and hash integrity verification.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.clustering import cluster_detections_spatiotemporal
from packages.events.pipeline import (
    RealEventConstructionService,
)
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight, PersistenceState
from packages.schemas.event import RealThermalEventDataset


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing a complete, calibrated ScientificConfig for testing."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
        spatial_cluster_radius_meters=1000.0,  # 1.0 km
        temporal_window_hours=2.0,  # 2.0 hours
        persistence_threshold_days=10.0,  # 10 days
        persistence_min_observations=3,  # 3 active days / events
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_det(
    det_id: str,
    lat: float,
    lon: float,
    dt: datetime,
    frp: float = 25.0,
    ti4: float = 350.0,
) -> Detection:
    """Helper to build a valid Detection domain model."""
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_test_01",
        acquired_at=dt,
        geometry=Coordinate(latitude=lat, longitude=lon),
        satellite="Suomi-NPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v2.0",
        raw_hash=f"raw_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=ti4,
        confidence="nominal",
        day_night=DayNight.DAY,
    )


class TestML011EventConstruction:
    """Comprehensive test suite for ML-011 event construction and source tracking."""

    def test_basic_spatiotemporal_clustering(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Nearby detections in window cluster; distant or separated do not."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)

        # Cluster 1: Two detections at Jamnagar flare point 500m apart within 30 min
        d1 = _make_det("det_01", 22.4500, 70.0500, t0, frp=30.0)
        d2 = _make_det("det_02", 22.4530, 70.0520, t0 + timedelta(minutes=30), frp=40.0)

        # Cluster 2: Spatial separation (> 10 km away at same time)
        d3 = _make_det("det_03", 22.5800, 70.2000, t0, frp=20.0)

        # Cluster 3: Temporal separation (> 5 hours later at same location as Cluster 1)
        d4 = _make_det("det_04", 22.4500, 70.0500, t0 + timedelta(hours=6), frp=25.0)

        clusters = cluster_detections_spatiotemporal(
            detections=[d1, d2, d3, d4],
            spatial_radius_meters=calibrated_config.spatial_cluster_radius_meters
            or 1000.0,
            temporal_window_hours=calibrated_config.temporal_window_hours or 2.0,
        )

        assert len(clusters) == 3
        # First cluster has d1 and d2
        cluster_ids = [{d.detection_id for d in c} for c in clusters]
        assert {"det_01", "det_02"} in cluster_ids
        assert {"det_03"} in cluster_ids
        assert {"det_04"} in cluster_ids

    def test_point_in_time_event_temporal_integrity(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Future detections (> as_of_time) are excluded from event derivation."""
        t0 = datetime(2026, 8, 1, 8, 0, 0, tzinfo=UTC)
        d_0800 = _make_det("det_0800", 22.4500, 70.0500, t0, frp=20.0)
        d_0830 = _make_det(
            "det_0830", 22.4502, 70.0502, t0 + timedelta(minutes=30), frp=30.0
        )
        d_0900 = _make_det(
            "det_0900", 22.4504, 70.0504, t0 + timedelta(hours=1), frp=40.0
        )
        d_1000 = _make_det(
            "det_1000", 22.4506, 70.0506, t0 + timedelta(hours=2), frp=50.0
        )

        all_detections = [d_0800, d_0830, d_0900, d_1000]

        # Query point-in-time state at 08:45 (only 08:00 and 08:30 available)
        pit_time = t0 + timedelta(minutes=45)
        pit_events = RealEventConstructionService.construct_point_in_time_events(
            detections=all_detections,
            as_of_time=pit_time,
            config=calibrated_config,
        )

        assert len(pit_events) == 1
        ev = pit_events[0]
        assert ev.detection_count == 2
        assert set(ev.detection_ids) == {"det_0800", "det_0830"}
        assert ev.mean_frp_mw == 25.0
        assert ev.ended_at == t0 + timedelta(minutes=30)
        # Verify future detections (09:00, 10:00) did not leak into point-in-time event
        assert "det_0900" not in ev.detection_ids
        assert "det_1000" not in ev.detection_ids

    def test_point_in_time_persistent_source_history_anti_leakage(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Future events cannot increase historical active days count or persistence."""
        t1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC)
        t3 = datetime(
            2026, 8, 12, 10, 0, 0, tzinfo=UTC
        )  # Past 10-day persistence threshold

        # 3 events at the same refinery stack across 12 days
        d1 = _make_det("d1", 22.4500, 70.0500, t1)
        d2 = _make_det("d2", 22.4500, 70.0500, t2)
        d3 = _make_det("d3", 22.4500, 70.0500, t3)

        ds_full = RealEventConstructionService.construct_events_and_sources(
            detections=[d1, d2, d3],
            config=calibrated_config,
        )

        assert ds_full.event_count == 3
        assert ds_full.persistent_source_count == 1
        full_source = ds_full.persistent_sources[0]
        assert full_source.active_days_count == 3
        assert full_source.persistence_state == PersistenceState.PERSISTENT

        # Query point-in-time source history as of Aug 2 (only event 1 exists)
        pit_sources_aug2 = (
            RealEventConstructionService.get_point_in_time_source_history(
                events=ds_full.events,
                as_of_time=datetime(2026, 8, 2, 0, 0, 0, tzinfo=UTC),
                config=calibrated_config,
            )
        )
        assert len(pit_sources_aug2) == 1
        src_aug2 = pit_sources_aug2[0]
        assert src_aug2.total_event_count == 1
        assert src_aug2.active_days_count == 1
        assert src_aug2.persistence_state == PersistenceState.INSUFFICIENT_HISTORY

        # Query point-in-time source history as of Aug 6 (events 1 & 2 exist)
        pit_sources_aug6 = (
            RealEventConstructionService.get_point_in_time_source_history(
                events=ds_full.events,
                as_of_time=datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC),
                config=calibrated_config,
            )
        )
        assert len(pit_sources_aug6) == 1
        src_aug6 = pit_sources_aug6[0]
        assert src_aug6.total_event_count == 2
        assert src_aug6.active_days_count == 2
        assert src_aug6.persistence_state == PersistenceState.RECURRING

    def test_determinism_and_content_addressability(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Identical inputs produce identical IDs, sources, and hashes."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        d1 = _make_det("d1", 22.4500, 70.0500, t0, frp=35.0)
        d2 = _make_det("d2", 22.4502, 70.0502, t0 + timedelta(minutes=20), frp=45.0)
        d3 = _make_det("d3", 22.4500, 70.0500, t0 + timedelta(days=2), frp=30.0)

        # Run 1 with standard order
        ds1 = RealEventConstructionService.construct_events_and_sources(
            detections=[d1, d2, d3],
            config=calibrated_config,
        )

        # Run 2 with reversed input order
        ds2 = RealEventConstructionService.construct_events_and_sources(
            detections=[d3, d1, d2],
            config=calibrated_config,
        )

        assert ds1.canonical_dataset_hash == ds2.canonical_dataset_hash
        assert [e.event_id for e in ds1.events] == [e.event_id for e in ds2.events]
        assert [s.source_id for s in ds1.persistent_sources] == [
            s.source_id for s in ds2.persistent_sources
        ]

    def test_end_to_end_real_fixture_activation_to_events(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Real fixture flows from ML-010 activation to ML-011 event construction."""
        fixture_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
        detection_dataset = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )

        event_dataset = RealEventConstructionService.construct_events_and_sources(
            detection_dataset=detection_dataset,
            config=calibrated_config,
            dataset_id="ds_real_events_jamnagar_v1.0.0",
        )

        assert isinstance(event_dataset, RealThermalEventDataset)
        assert event_dataset.detection_dataset_id == "ds_real_firms_v1.0.0"
        assert (
            event_dataset.detection_dataset_hash
            == detection_dataset.manifest.canonical_dataset_hash
        )
        assert event_dataset.event_count > 0
        assert event_dataset.persistent_source_count > 0

        # Validate provenance linkage
        for ev in event_dataset.events:
            assert len(ev.detection_ids) >= 1
            for det_id in ev.detection_ids:
                # Member detection must exist in originating detection dataset
                assert any(
                    d.detection_id == det_id for d in detection_dataset.detections
                )

        for src in event_dataset.persistent_sources:
            assert len(src.linked_event_ids) >= 1
            for ev_id in src.linked_event_ids:
                assert any(e.event_id == ev_id for e in event_dataset.events)

    def test_save_and_load_event_dataset_with_tamper_detection(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Event dataset serializes and reloads cleanly, detecting tampered records."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        d1 = _make_det("d1", 22.4500, 70.0500, t0)
        d2 = _make_det("d2", 22.4500, 70.0500, t0 + timedelta(days=2))

        dataset = RealEventConstructionService.construct_events_and_sources(
            detections=[d1, d2],
            config=calibrated_config,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = RealEventConstructionService.save_dataset(dataset, tmp_dir)
            assert out_path.exists()

            # 1. Clean reload
            reloaded = RealEventConstructionService.load_dataset(out_path)
            assert reloaded.canonical_dataset_hash == dataset.canonical_dataset_hash
            assert len(reloaded.events) == len(dataset.events)

            # 2. Tampered reload
            import json

            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["events"][0]["mean_frp_mw"] = 8888.0
            out_path.write_text(json.dumps(data), encoding="utf-8")

            with pytest.raises(ValueError, match="Thermal event dataset hash mismatch"):
                RealEventConstructionService.load_dataset(out_path)
