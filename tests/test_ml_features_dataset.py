"""Unit tests for FeatureExtractor, FeatureDatasetBuilder, and feature catalogs."""

import math
from datetime import UTC, datetime, timedelta

import pytest

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
from packages.schemas.ml import (
    FeatureEligibilityStatus,
    SplitStrategy,
    TargetUnit,
)
from packages.schemas.source import PersistentSource
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.reporting import (
    generate_dataset_quality_report,
    generate_feature_catalog_json,
    generate_feature_catalog_markdown,
)
from services.ml.features.standard_set import (
    APPROVED_FEATURES,
    DISQUALIFIED_CANDIDATES,
    get_standard_feature_registry,
)


def _create_sample_detection(
    det_id: str,
    lat: float,
    lon: float,
    acq_time: datetime,
    frp: float = 25.0,
    bt: float = 330.0,
    sat: str = "SNPP",
    inst: str = "VIIRS",
    day_night: DayNight = DayNight.DAY,
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_20260101",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=acq_time,
        satellite=sat,
        instrument=inst,
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=bt,
        confidence="nominal",
        day_night=day_night,
    )


def _create_sample_event(
    event_id: str,
    det_ids: list[str],
    lat: float,
    lon: float,
    start_time: datetime,
    end_time: datetime,
) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=det_ids,
        detection_count=len(det_ids),
        started_at=start_time,
        ended_at=end_time,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="cfg_event_v1",
        formation_configuration_version="v1.0",
    )


class TestMLFeatureDataset:
    """Test suite validating standard feature extraction and dataset building."""

    def test_standard_feature_registry_contains_approved_and_disqualified(
        self,
    ) -> None:
        """Registry is populated with approved and disqualified features."""
        registry = get_standard_feature_registry()
        all_features = registry.list_features()
        assert len(all_features) >= 30

        approved = [
            f
            for f in all_features
            if f.eligibility_status == FeatureEligibilityStatus.APPROVED
        ]
        assert len(approved) == len(APPROVED_FEATURES)
        assert any(f.feature_name == "frp_mean_mw" for f in approved)
        assert any(f.feature_name == "facility_distance_meters" for f in approved)

        disqualified = [
            f
            for f in all_features
            if f.eligibility_status != FeatureEligibilityStatus.APPROVED
        ]
        assert len(disqualified) == len(DISQUALIFIED_CANDIDATES)
        assert any(f.feature_name == "reference_class" for f in disqualified)
        assert any(f.feature_name == "raw_event_id" for f in disqualified)

    def test_feature_extractor_extracts_thermal_core_correctly(self) -> None:
        """FeatureExtractor computes accurate aggregations on member detections."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        t2 = datetime(2026, 1, 15, 11, 0, 0, tzinfo=UTC)

        d1 = _create_sample_detection("d1", 22.47, 70.05, t0, frp=10.0, bt=320.0)
        d2 = _create_sample_detection("d2", 22.48, 70.06, t1, frp=20.0, bt=340.0)
        d3 = _create_sample_detection("d3", 22.49, 70.07, t2, frp=30.0, bt=360.0)

        event = _create_sample_event(
            "evt_001", ["d1", "d2", "d3"], 22.48, 70.06, t0, t2
        )
        as_of = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d1, d2, d3],
            as_of_time=as_of,
        )

        assert record.entity_id == "evt_001"
        assert record.prediction_unit == TargetUnit.EVENT
        assert record.features["detection_count"] == 3

        assert math.isclose(float(record.features["frp_mean_mw"] or 0.0), 20.0)
        assert math.isclose(float(record.features["frp_max_mw"] or 0.0), 30.0)
        assert math.isclose(float(record.features["frp_min_mw"] or 0.0), 10.0)
        assert math.isclose(float(record.features["frp_sum_mw"] or 0.0), 60.0)
        assert math.isclose(float(record.features["frp_std_mw"] or 0.0), 10.0)
        assert math.isclose(float(record.features["duration_hours"] or 0.0), 1.0)
        assert math.isclose(float(record.features["temporal_density"] or 0.0), 3.0)
        assert math.isclose(
            float(record.features["brightness_mean_kelvin"] or 0.0), 340.0
        )
        assert math.isclose(
            float(record.features["brightness_max_kelvin"] or 0.0), 360.0
        )
        assert record.features["satellite_platform_diversity"] == 1
        assert record.features["sensor_instrument"] == "VIIRS"

    def test_feature_extractor_with_context_and_persistence(self) -> None:
        """FeatureExtractor integrates context evidence and persistence source."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_sample_detection("d1", 22.47, 70.05, t0, frp=15.0)
        event = _create_sample_event("evt_002", ["d1"], 22.47, 70.05, t0, t0)

        # Context evidence
        context = [
            ContextEvidence(
                context_id="ctx_001",
                source_type="osm",
                context_type=ContextType.OIL_GAS,
                geometry=Coordinate(latitude=22.471, longitude=70.051),
                availability_state=EvidenceAvailabilityState.AVAILABLE,
                distance_to_event_meters=150.0,
            ),
            ContextEvidence(
                context_id="ctx_002",
                source_type="wri",
                context_type=ContextType.POWER,
                geometry=Coordinate(latitude=22.50, longitude=70.10),
                availability_state=EvidenceAvailabilityState.AVAILABLE,
                distance_to_event_meters=5500.0,
            ),
        ]

        # Persistence source
        source = PersistentSource(
            source_id="src_perm_001",
            linked_event_ids=["evt_001", "evt_002"],
            total_event_count=2,
            centroid_geometry=Coordinate(latitude=22.47, longitude=70.05),
            first_seen_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_seen_at=t0,
            active_days_count=12,
            persistence_state=PersistenceState.PERSISTENT,
            persistence_configuration_id="cfg_pers_v1",
            persistence_configuration_version="v1.0",
            recurrence_ratio=0.85,
        )

        as_of = datetime(2026, 1, 15, 11, 0, 0, tzinfo=UTC)
        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d1],
            as_of_time=as_of,
            source=source,
            context_evidence=context,
        )

        # Context features
        assert record.features["facility_distance_meters"] == 150.0
        assert record.features["facility_context_type"] == "oil_gas"
        assert record.features["is_near_industrial_facility"] is True
        assert record.features["power_plant_distance_meters"] == 5500.0

        # Persistence features
        assert record.features["persistence_active_days"] == 12
        assert record.features["persistence_total_events"] == 2
        assert record.features["persistence_recurrence_ratio"] == 0.85
        assert record.features["is_persistent_source"] is True
        assert record.features["persistence_state"] == "persistent"

    def test_missingness_preservation_and_indicators(self) -> None:
        """Missing values are preserved as None (missing != 0) with explicit flags."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_sample_detection("d1", 22.47, 70.05, t0, frp=15.0)
        event = _create_sample_event("evt_003", ["d1"], 22.47, 70.05, t0, t0)

        # Zero context provided
        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d1],
            as_of_time=t0,
            context_evidence=None,
            source=None,
        )

        # Missing values are None, NOT 0.0 or 0
        assert record.features["facility_distance_meters"] is None
        assert record.features["power_plant_distance_meters"] is None
        assert record.features["water_distance_meters"] is None
        assert record.features["time_since_previous_event_hours"] is None

        # Explicit missingness flags
        assert record.missingness_flags["facility_distance_meters_is_missing"] is True
        assert (
            record.missingness_flags["power_plant_distance_meters_is_missing"] is True
        )
        assert record.missingness_flags["detection_count_is_missing"] is False

    def test_feature_dataset_builder_determinism_and_hashing(self) -> None:
        """Dataset builder produces identical SHA-256 hash across shuffled inputs."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 1, 16, 10, 0, 0, tzinfo=UTC)

        d1 = _create_sample_detection("d1", 22.47, 70.05, t0, frp=15.0)
        d2 = _create_sample_detection("d2", 22.50, 70.10, t1, frp=35.0)

        e1 = _create_sample_event("evt_a", ["d1"], 22.47, 70.05, t0, t0)
        e2 = _create_sample_event("evt_b", ["d2"], 22.50, 70.10, t1, t1)

        tuple_1 = (e1, [d1], t0 + timedelta(hours=1), None, None, None)
        tuple_2 = (e2, [d2], t1 + timedelta(hours=1), None, None, None)

        builder = FeatureDatasetBuilder()

        # Build with order: [evt_a, evt_b]
        ds_1 = builder.extract_and_build_dataset(
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            target_id="target_thermal_phenomenon",
            geographic_scope="IND_JAMNAGAR",
            temporal_start=t0,
            temporal_end=t1 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=[tuple_1, tuple_2],
        )

        # Build with reversed order: [evt_b, evt_a]
        ds_2 = builder.extract_and_build_dataset(
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            target_id="target_thermal_phenomenon",
            geographic_scope="IND_JAMNAGAR",
            temporal_start=t0,
            temporal_end=t1 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=[tuple_2, tuple_1],
        )

        assert ds_1.manifest.sha256_hash == ds_2.manifest.sha256_hash
        assert len(ds_1.records) == 2
        assert ds_1.records[0].entity_id == "evt_a"
        assert ds_1.records[1].entity_id == "evt_b"

    def test_showcase_isolation_in_dataset_builder(self) -> None:
        """Showcase records (DATASET-003) are excluded from benchmark records."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_sample_detection("d1", 22.47, 70.05, t0)
        d2 = _create_sample_detection("d2", 22.50, 70.10, t0)

        e1 = _create_sample_event("evt_regular", ["d1"], 22.47, 70.05, t0, t0)
        e2 = _create_sample_event("evt_showcase", ["d2"], 22.50, 70.10, t0, t0)

        tuple_1 = (e1, [d1], t0, None, None, None)
        tuple_2 = (e2, [d2], t0, None, None, None)

        builder = FeatureDatasetBuilder()
        ds = builder.extract_and_build_dataset(
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            target_id="target_thermal_phenomenon",
            geographic_scope="IND_JAMNAGAR",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=[tuple_1, tuple_2],
            isolated_showcase_ids=["evt_showcase"],
        )

        # evt_showcase must NOT be in dataset records
        assert len(ds.records) == 1
        assert ds.records[0].entity_id == "evt_regular"
        assert ds.manifest.record_count == 1

    def test_duplicate_event_rejection(self) -> None:
        """Duplicate event records in dataset build raise ValueError."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_sample_detection("d1", 22.47, 70.05, t0)
        e1 = _create_sample_event("evt_dup", ["d1"], 22.47, 70.05, t0, t0)

        tuple_1 = (e1, [d1], t0, None, None, None)
        tuple_dup = (e1, [d1], t0, None, None, None)

        builder = FeatureDatasetBuilder()
        with pytest.raises(ValueError, match="Duplicate records detected"):
            builder.extract_and_build_dataset(
                dataset_id="ds_jamnagar_v1",
                dataset_version="v1.0.0",
                target_id="target_thermal_phenomenon",
                geographic_scope="IND_JAMNAGAR",
                temporal_start=t0,
                temporal_end=t0 + timedelta(days=1),
                split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
                event_tuples=[tuple_1, tuple_dup],
            )

    def test_feature_reporting_utilities(self) -> None:
        """Reporting utilities generate valid Markdown and JSON summaries."""
        md = generate_feature_catalog_markdown()
        assert "| Feature Name |" in md
        assert "`frp_mean_mw`" in md
        assert "`reference_class`" in md

        json_catalog = generate_feature_catalog_json()
        assert json_catalog["total_features"] >= 30
        assert any(f["feature_name"] == "frp_mean_mw" for f in json_catalog["features"])

        # Dataset quality report
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_sample_detection("d1", 22.47, 70.05, t0, frp=15.0)
        e1 = _create_sample_event("evt_rep", ["d1"], 22.47, 70.05, t0, t0)
        tuple_1 = (e1, [d1], t0, None, None, None)

        builder = FeatureDatasetBuilder()
        ds = builder.extract_and_build_dataset(
            dataset_id="ds_jamnagar_rep",
            dataset_version="v1.0.0",
            target_id="target_thermal_phenomenon",
            geographic_scope="IND_JAMNAGAR",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=[tuple_1],
        )
        report = generate_dataset_quality_report(ds)
        assert report["dataset_id"] == "ds_jamnagar_rep"
        assert report["record_count"] == 1
        assert "missingness_summary" in report
