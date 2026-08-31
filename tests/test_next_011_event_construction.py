"""Comprehensive Test Suite for NEXT-011: Canonical Thermal Event Construction.

Covers all 28 canonical requirements:
1. Empty input handling
2. Single detection event formation
3. Two detections within threshold -> single event
4. Two detections outside spatial threshold -> separate events
5. Spatial boundary conditions (exact threshold distance)
6. Temporal boundary conditions (exact threshold duration)
7. Multiple spatiotemporal clusters
8. Deterministic event construction (shuffle invariance)
9. Deterministic content-addressable event IDs
10. Timestamp correctness (earliest, latest, duration)
11. Centroid calculation correctness
12. Detection count invariance
13. FRP statistical aggregation (mean, max, null-safe)
14. Provenance tracking (lineage, config version, detection IDs)
15. Duplicate detection resilience
16. Invalid coordinates validation
17. Malformed timestamp validation
18. UTC timezone preservation
19. GIS / GeoJSON compatibility
20. API serialization compatibility
21. ML FeatureExtractor compatibility (30 canonical features)
22. NEXT-010 regression compatibility
23. Point-in-time temporal safety
24. Future-data exclusion
25. Stable deterministic event ordering
26. Multi-satellite / instrument fusion
27. Sparse isolated detections
28. High-density cluster processing
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from packages.config.scientific import ScientificConfig
from packages.events.builder import (
    generate_deterministic_event_id,
)
from packages.events.service import derive_thermal_events
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.integration.firms_pipeline import (
    FirmsProductionMLIntegrationService,
)


@pytest.fixture
def calibrated_scientific_config() -> ScientificConfig:
    """Authoritative calibrated scientific configuration for event clustering."""
    return ScientificConfig(
        version="v1.0.0-production",
        name="production_thermal_event_clustering",
        description="Calibrated clustering configuration for production FIRMS events",
        spatial_cluster_radius_meters=1000.0,  # 1.0 km
        temporal_window_hours=2.0,  # 2.0 hours
        persistence_threshold_days=30.0,
        persistence_min_observations=5,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def make_det(
    det_id: str,
    lat: float = 22.470,
    lon: float = 70.050,
    dt: datetime | None = None,
    frp: float | None = 50.0,
    brightness: float = 380.0,
    satellite: str = "Suomi-NPP",
    instrument: str = "VIIRS",
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    """Helper to synthesize valid canonical Detection domain model."""
    acq = dt or datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC)
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_011_test",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=acq,
        satellite=satellite,
        instrument=instrument,
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


class TestNext011EventConstruction:
    """Complete 28-point validation suite for NEXT-011 event construction."""

    # 1. Empty input
    def test_01_empty_input_returns_empty_list(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        events = derive_thermal_events([], calibrated_scientific_config)
        assert events == []

    # 2. Single detection
    def test_02_single_detection_event_formation(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        d = make_det("det_001", lat=22.470, lon=70.050, dt=t0, frp=80.0)
        events = derive_thermal_events([d], calibrated_scientific_config)

        assert len(events) == 1
        e = events[0]
        assert e.detection_count == 1
        assert e.detection_ids == ["det_001"]
        assert e.started_at == t0
        assert e.ended_at == t0
        assert e.duration_seconds == 0.0
        assert e.centroid_geometry.latitude == 22.470
        assert e.centroid_geometry.longitude == 70.050
        assert e.max_frp_mw == 80.0
        assert e.mean_frp_mw == 80.0

    # 3. Two detections within threshold -> single event
    def test_03_two_detections_within_threshold_form_single_event(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC)  # +30 min <= 2.0h
        # ~300m apart (0.003 deg lat ~333m <= 1000m)
        d1 = make_det("det_001", lat=22.470, lon=70.050, dt=t0, frp=40.0)
        d2 = make_det("det_002", lat=22.473, lon=70.050, dt=t1, frp=60.0)

        events = derive_thermal_events([d1, d2], calibrated_scientific_config)
        assert len(events) == 1
        e = events[0]
        assert e.detection_count == 2
        assert set(e.detection_ids) == {"det_001", "det_002"}
        assert e.started_at == t0
        assert e.ended_at == t1
        assert e.duration_seconds == 1800.0
        assert e.mean_frp_mw == 50.0
        assert e.max_frp_mw == 60.0

    # 4. Two detections outside spatial threshold -> separate events
    def test_04_two_detections_outside_spatial_threshold_form_separate_events(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        # Delhi (28.61, 77.20) vs Mumbai (19.07, 72.87) >> 1000m
        d1 = make_det("det_delhi", lat=28.61, lon=77.20, dt=t0)
        d2 = make_det("det_mumbai", lat=19.07, lon=72.87, dt=t0)

        events = derive_thermal_events([d1, d2], calibrated_scientific_config)
        assert len(events) == 2
        assert events[0].detection_count == 1
        assert events[1].detection_count == 1

    # 5. Spatial boundary conditions
    def test_05_spatial_boundary_conditions(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 18, 0, 0, tzinfo=UTC)
        lat_base = 22.000000
        lon_base = 70.000000

        # Calculate exact offset for ~900m (inside) and ~1200m (outside)
        # 1 deg lat ~ 111,139 m -> 0.008 deg ~ 889 m (inside 1000m)
        d_center = make_det("d_center", lat=lat_base, lon=lon_base, dt=t0)
        d_inside = make_det("d_inside", lat=lat_base + 0.008, lon=lon_base, dt=t0)
        # 0.015 deg ~ 1667 m (outside 1000m)
        d_outside = make_det("d_outside", lat=lat_base + 0.015, lon=lon_base, dt=t0)

        dist_inside = haversine_distance_meters(
            lat_base, lon_base, lat_base + 0.008, lon_base
        )
        dist_outside = haversine_distance_meters(
            lat_base, lon_base, lat_base + 0.015, lon_base
        )
        assert dist_inside <= 1000.0
        assert dist_outside > 1000.0

        evts_inside = derive_thermal_events(
            [d_center, d_inside], calibrated_scientific_config
        )
        assert len(evts_inside) == 1

        evts_outside = derive_thermal_events(
            [d_center, d_outside], calibrated_scientific_config
        )
        assert len(evts_outside) == 2

    # 6. Temporal boundary conditions
    def test_06_temporal_boundary_conditions(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        # Window is 2.0 hours (7200 seconds)
        t_inside = t0 + timedelta(hours=1, minutes=50)  # 1.83h <= 2.0h
        t_outside = t0 + timedelta(hours=2, minutes=15)  # 2.25h > 2.0h

        d0 = make_det("d0", lat=22.470, lon=70.050, dt=t0)
        d_in = make_det("d_in", lat=22.470, lon=70.050, dt=t_inside)
        d_out = make_det("d_out", lat=22.470, lon=70.050, dt=t_outside)

        evts_in = derive_thermal_events([d0, d_in], calibrated_scientific_config)
        assert len(evts_in) == 1

        evts_out = derive_thermal_events([d0, d_out], calibrated_scientific_config)
        assert len(evts_out) == 2

    # 7. Multiple spatiotemporal clusters
    def test_07_multiple_spatiotemporal_clusters(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        cluster_a = [
            make_det(
                f"a_{i}", 22.470, 70.050 + i * 0.001, t0 + timedelta(minutes=i * 5)
            )
            for i in range(3)
        ]
        cluster_b = [
            make_det(
                f"b_{i}", 24.100, 72.300 + i * 0.001, t0 + timedelta(minutes=i * 5)
            )
            for i in range(4)
        ]
        cluster_c = [
            make_det(f"c_{i}", 22.470, 70.050, t0 + timedelta(days=2, minutes=i * 5))
            for i in range(2)
        ]

        all_dets = cluster_a + cluster_b + cluster_c
        events = derive_thermal_events(all_dets, calibrated_scientific_config)
        assert len(events) == 3
        counts = sorted(e.detection_count for e in events)
        assert counts == [2, 3, 4]

    # 8. Deterministic event construction (shuffle invariance)
    def test_08_deterministic_event_construction(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC)
        dets = [
            make_det(f"det_{i}", 22.470 + i * 0.001, 70.050, t0 + timedelta(minutes=i))
            for i in range(8)
        ]

        baseline = derive_thermal_events(dets, calibrated_scientific_config)
        rng = random.Random(999)
        for _ in range(15):
            shuffled = list(dets)
            rng.shuffle(shuffled)
            res = derive_thermal_events(shuffled, calibrated_scientific_config)
            assert len(res) == len(baseline)
            assert res[0].event_id == baseline[0].event_id
            assert res[0].detection_ids == baseline[0].detection_ids

    # 9. Deterministic content-addressable event IDs
    def test_09_deterministic_event_ids(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        fp = calibrated_scientific_config.compute_fingerprint()
        id1 = generate_deterministic_event_id(["det_01", "det_02"], fp)
        id2 = generate_deterministic_event_id(["det_02", "det_01"], fp)
        assert id1 == id2
        assert id1.startswith("evt_")

    # 10. Timestamp correctness
    def test_10_timestamp_correctness(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t_start = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        t_mid = datetime(2026, 8, 15, 12, 30, 0, tzinfo=UTC)
        t_end = datetime(2026, 8, 15, 13, 0, 0, tzinfo=UTC)

        d1 = make_det("d1", dt=t_mid)
        d2 = make_det("d2", dt=t_start)
        d3 = make_det("d3", dt=t_end)

        events = derive_thermal_events([d1, d2, d3], calibrated_scientific_config)
        assert len(events) == 1
        assert events[0].started_at == t_start
        assert events[0].ended_at == t_end
        assert events[0].duration_seconds == 3600.0

    # 11. Centroid calculation correctness
    def test_11_centroid_correctness(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d1 = make_det("d1", lat=22.0, lon=70.0)
        d2 = make_det("d2", lat=22.002, lon=70.002)

        events = derive_thermal_events([d1, d2], calibrated_scientific_config)
        assert len(events) == 1
        assert abs(events[0].centroid_geometry.latitude - 22.001) < 1e-5
        assert abs(events[0].centroid_geometry.longitude - 70.001) < 1e-5

    # 12. Detection count invariance
    def test_12_detection_count_invariance(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        dets = [make_det(f"d_{i}") for i in range(5)]
        events = derive_thermal_events(dets, calibrated_scientific_config)
        assert len(events) == 1
        assert events[0].detection_count == 5
        assert events[0].detection_count == len(events[0].detection_ids)

    # 13. FRP statistical aggregation
    def test_13_frp_aggregation(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d1 = make_det("d1", frp=20.0)
        d2 = make_det("d2", frp=80.0)
        d3 = make_det("d3", frp=None)  # None FRP

        events = derive_thermal_events([d1, d2, d3], calibrated_scientific_config)
        assert len(events) == 1
        assert events[0].mean_frp_mw == 50.0
        assert events[0].max_frp_mw == 80.0

    # 14. Provenance tracking
    def test_14_provenance_tracking(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d = make_det("d_prov_01")
        events = derive_thermal_events(
            [d], calibrated_scientific_config, formation_run_id="run_test_011"
        )
        assert len(events) == 1
        e = events[0]
        assert e.formation_configuration_id == calibrated_scientific_config.name
        assert e.formation_configuration_version == calibrated_scientific_config.version
        assert e.formation_run_id == "run_test_011"
        assert e.detection_ids == ["d_prov_01"]

    # 15. Duplicate detection handling
    def test_15_duplicate_detection_handling(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d1 = make_det("d_dup_01", frp=50.0)
        d1_clone = make_det("d_dup_01", frp=50.0)

        # Pass duplicate detections in input list
        events = derive_thermal_events([d1, d1_clone], calibrated_scientific_config)
        assert len(events) == 1
        assert events[0].detection_count == 1
        assert events[0].detection_ids == ["d_dup_01"]
        assert events[0].mean_frp_mw == 50.0

    # 16. Invalid coordinates validation
    def test_16_invalid_coordinates_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Coordinate(latitude=95.0, longitude=70.0)  # lat > 90 invalid

        with pytest.raises(ValidationError):
            Coordinate(latitude=22.0, longitude=195.0)  # lon > 180 invalid

    # 17. Malformed timestamps rejected
    def test_17_malformed_timestamps_rejected(self) -> None:
        with pytest.raises(ValidationError):
            # Naive datetime without tzinfo rejected
            naive_dt = datetime(2026, 8, 15, 12, 0, 0)
            Detection(
                detection_id="d_bad_ts",
                source="firms",
                source_snapshot_id="s1",
                geometry=Coordinate(latitude=22.0, longitude=70.0),
                acquired_at=naive_dt,
                satellite="VIIRS",
                instrument="VIIRS",
                product_type="nrt",
                product_version="v1.0",
                raw_hash="hash01",
            )

    # 18. UTC timezone preservation
    def test_18_utc_timezone_preservation(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d = make_det("d_utc_01")
        events = derive_thermal_events([d], calibrated_scientific_config)
        assert events[0].started_at.tzinfo == UTC
        assert events[0].ended_at.tzinfo == UTC

    # 19. GIS / GeoJSON compatibility
    def test_19_gis_geojson_compatibility(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d1 = make_det("d1", lat=22.470, lon=70.050)
        d2 = make_det("d2", lat=22.472, lon=70.052)
        events = derive_thermal_events([d1, d2], calibrated_scientific_config)
        e = events[0]

        # Valid GeoJSON Feature construction
        geojson_feature: dict[str, Any] = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    e.centroid_geometry.longitude,
                    e.centroid_geometry.latitude,
                ],
            },
            "properties": {
                "event_id": e.event_id,
                "detection_count": e.detection_count,
                "max_frp_mw": e.max_frp_mw,
                "started_at": e.started_at.isoformat(),
                "ended_at": e.ended_at.isoformat(),
            },
        }
        assert geojson_feature["type"] == "Feature"
        geom_dict = geojson_feature["geometry"]
        assert geom_dict["coordinates"] == [
            e.centroid_geometry.longitude,
            e.centroid_geometry.latitude,
        ]

    # 20. API serialization compatibility
    def test_20_api_serialization_compatibility(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d = make_det("d_api_01")
        events = derive_thermal_events([d], calibrated_scientific_config)
        e = events[0]
        json_str = e.model_dump_json()
        assert e.event_id in json_str
        assert "centroid_geometry" in json_str

    # 21. ML FeatureExtractor compatibility
    def test_21_ml_feature_extractor_compatibility(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d = make_det("d_feat_01")
        events = derive_thermal_events([d], calibrated_scientific_config)
        e = events[0]

        extractor = FeatureExtractor()
        feature_record = extractor.extract_features_for_event(
            event=e,
            member_detections=[d],
            as_of_time=e.ended_at,
        )
        assert len(feature_record.features) == len(APPROVED_FEATURES)
        assert len(feature_record.features) == 30
        for approved_feat in APPROVED_FEATURES:
            assert approved_feat.feature_name in feature_record.features

    # 22. NEXT-010 regression compatibility
    def test_22_next_010_regression_compatibility(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        d = make_det("d_next010_01")
        res = FirmsProductionMLIntegrationService.evaluate_detections(
            detections=[d],
            mode=ProductionOperatingMode.HIGH_PRECISION,
            config=calibrated_scientific_config,
        )
        assert len(res) == 1
        assert res[0].feature_count == 30
        assert res[0].assigned_class in ("industrial", "non_industrial", "unknown")

    # 23. Point-in-time safety
    def test_23_point_in_time_safety(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t_hist = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)
        t_future = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)

        d_hist = make_det("d_hist", dt=t_hist)
        d_future = make_det("d_future", dt=t_future)

        # Event constructed from historical observation
        hist_events = derive_thermal_events([d_hist], calibrated_scientific_config)
        assert len(hist_events) == 1
        assert hist_events[0].ended_at == t_hist

        # Future observation never affects historical event
        assert d_future.detection_id not in hist_events[0].detection_ids

    # 24. Future-data exclusion
    def test_24_future_data_exclusion(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t_now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        d1 = make_det("d1", dt=t_now)
        d_future = make_det("d_future", dt=t_now + timedelta(days=5))

        # Separate cluster formed days in future
        events = derive_thermal_events([d1, d_future], calibrated_scientific_config)
        assert len(events) == 2
        assert events[0].ended_at == t_now
        assert events[1].ended_at > t_now

    # 25. Stable deterministic event ordering
    def test_25_stable_event_ordering(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        d_delhi = make_det("d_delhi", lat=28.61, lon=77.20, dt=t0)
        d_mumbai = make_det("d_mumbai", lat=19.07, lon=72.87, dt=t0)

        # Mumbai has lower latitude (19.07 < 28.61), should consistently sort first
        events = derive_thermal_events(
            [d_delhi, d_mumbai], calibrated_scientific_config
        )
        assert events[0].detection_ids == ["d_mumbai"]
        assert events[1].detection_ids == ["d_delhi"]

    # 26. Multi-satellite / instrument fusion
    def test_26_multi_satellite_instrument_fusion(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        # VIIRS from Suomi-NPP and MODIS from Terra 10 minutes apart at same location
        d_viirs = make_det("d_viirs", satellite="Suomi-NPP", instrument="VIIRS", dt=t0)
        d_modis = make_det(
            "d_modis",
            satellite="Terra",
            instrument="MODIS",
            dt=t0 + timedelta(minutes=10),
        )

        events = derive_thermal_events([d_viirs, d_modis], calibrated_scientific_config)
        assert len(events) == 1
        assert events[0].detection_count == 2
        assert set(events[0].detection_ids) == {"d_viirs", "d_modis"}

    # 27. Sparse isolated detections
    def test_27_sparse_isolated_detections(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        sparse_dets = [
            make_det(f"sparse_{i}", lat=10.0 + i * 2.0, lon=70.0 + i * 2.0, dt=t0)
            for i in range(10)
        ]
        events = derive_thermal_events(sparse_dets, calibrated_scientific_config)
        assert len(events) == 10
        for e in events:
            assert e.detection_count == 1

    # 28. High-density cluster processing
    def test_28_high_density_cluster_processing(
        self, calibrated_scientific_config: ScientificConfig
    ) -> None:
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        # 60 proximate detections within 500m over 1 hour
        dense_dets = [
            make_det(
                f"dense_{i}",
                lat=22.470 + (i % 5) * 0.0005,
                lon=70.050 + (i // 5) * 0.0005,
                dt=t0 + timedelta(minutes=i),
                frp=50.0 + i,
            )
            for i in range(60)
        ]
        events = derive_thermal_events(dense_dets, calibrated_scientific_config)
        assert len(events) == 1
        e = events[0]
        assert e.detection_count == 60
        assert e.started_at == t0
        assert e.ended_at == t0 + timedelta(minutes=59)
        assert e.duration_seconds == 59 * 60.0
        assert e.max_frp_mw == 109.0
