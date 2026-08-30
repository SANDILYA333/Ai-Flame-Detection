"""Study-area feasibility analysis CLI for candidate Indian regions (DATA-001)."""

import argparse
import sys
from datetime import UTC, datetime, timedelta

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.feasibility import (
    PROVISIONAL_CANDIDATE_AREAS,
    CandidateReferencePoint,
    evaluate_study_area_feasibility,
    generate_markdown_feasibility_report,
    get_candidate_study_area,
    run_comparative_feasibility_harness,
)
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight


def _generate_synthetic_benchmark_fixtures() -> tuple[
    list[Detection], list[ContextFeature], list[CandidateReferencePoint]
]:
    """Generate realistic demonstration fixtures for candidate Indian study areas."""
    detections: list[Detection] = []
    context_features: list[ContextFeature] = []
    reference_points: list[CandidateReferencePoint] = []

    base_time = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)

    # 1. Jamnagar / Kutch (Petrochemical Refinery Flaring Hub)
    for i in range(40):
        t = base_time + timedelta(days=i, hours=(i % 4) * 6)
        detections.append(
            Detection(
                detection_id=f"DET-JAM-{i:03d}",
                source="firms",
                source_snapshot_id="SNAP-JAM-001",
                acquired_at=t,
                geometry=Coordinate(
                    latitude=22.450 + (i % 3) * 0.002,
                    longitude=70.050 + (i % 2) * 0.002,
                ),
                satellite="NOAA-20" if i % 2 == 0 else "SNPP",
                instrument="VIIRS",
                product_type="nrt",
                product_version="v2.0",
                raw_hash=f"hash_jam_{i}",
                frp_mw=35.0 + (i % 15) * 5.0,
                brightness_ti4_k=355.0 + (i % 10),
                brightness_ti5_k=295.0,
                confidence="nominal",
                scan_km=0.375,
                track_km=0.375,
                day_night=DayNight.NIGHT if i % 2 == 0 else DayNight.DAY,
            )
        )
    context_features.extend(
        [
            ContextFeature(
                feature_id="CTX-JAM-01",
                provider="osm",
                dataset_name="osm_industrial_polygons",
                dataset_version="2026-08-01",
                context_type=ContextType.OIL_GAS,
                geometry=Coordinate(latitude=22.451, longitude=70.051),
                facility_name="Jamnagar Refinery Complex",
            ),
            ContextFeature(
                feature_id="CTX-JAM-02",
                provider="osm",
                dataset_name="osm_industrial_polygons",
                dataset_version="2026-08-01",
                context_type=ContextType.POWER,
                geometry=Coordinate(latitude=22.430, longitude=70.010),
                facility_name="Sikka Thermal Power Station",
            ),
        ]
    )
    reference_points.append(
        CandidateReferencePoint(
            point_id="REF-JAM-01",
            source_name="GGIT_FLARING",
            tier="TIER_A",
            geometry=Coordinate(latitude=22.452, longitude=70.052),
            facility_name="Jamnagar Flare Stack 1A",
        )
    )

    # 2. Singrauli / Sonbhadra (Coal Thermal Power Hub)
    for i in range(25):
        t = base_time + timedelta(days=i * 2, hours=(i % 3) * 8)
        detections.append(
            Detection(
                detection_id=f"DET-SNG-{i:03d}",
                source="firms",
                source_snapshot_id="SNAP-SNG-001",
                acquired_at=t,
                geometry=Coordinate(
                    latitude=24.100 + (i % 2) * 0.005,
                    longitude=82.600 + (i % 3) * 0.005,
                ),
                satellite="NOAA-20",
                instrument="VIIRS",
                product_type="nrt",
                product_version="v2.0",
                raw_hash=f"hash_sng_{i}",
                frp_mw=45.0 + (i % 20) * 3.0,
                brightness_ti4_k=360.0,
                brightness_ti5_k=300.0,
                confidence="nominal",
                scan_km=0.375,
                track_km=0.375,
                day_night=DayNight.NIGHT,
            )
        )
    context_features.append(
        ContextFeature(
            feature_id="CTX-SNG-01",
            provider="osm",
            dataset_name="osm_industrial_polygons",
            dataset_version="2026-08-01",
            context_type=ContextType.POWER,
            geometry=Coordinate(latitude=24.102, longitude=82.603),
            facility_name="NTPC Singrauli Super Thermal Power",
        )
    )
    reference_points.append(
        CandidateReferencePoint(
            point_id="REF-SNG-01",
            source_name="GEM_POWER",
            tier="TIER_B",
            geometry=Coordinate(latitude=24.103, longitude=82.604),
            facility_name="Singrauli Thermal Power Boiler Unit",
        )
    )

    # 3. Punjab Agricultural (Transient Stubble Burning)
    for i in range(15):
        t = base_time + timedelta(
            hours=i * 4
        )  # 15 detections within 2.5 days (acute transient burst)
        detections.append(
            Detection(
                detection_id=f"DET-PB-{i:03d}",
                source="firms",
                source_snapshot_id="SNAP-PB-001",
                acquired_at=t,
                geometry=Coordinate(
                    latitude=30.450 + (i * 0.02), longitude=75.800 + (i * 0.03)
                ),
                satellite="NOAA-20",
                instrument="VIIRS",
                product_type="nrt",
                product_version="v2.0",
                raw_hash=f"hash_pb_{i}",
                frp_mw=15.0 + (i % 10),
                brightness_ti4_k=330.0,
                brightness_ti5_k=290.0,
                confidence="nominal",
                scan_km=0.375,
                track_km=0.375,
                day_night=DayNight.DAY,
            )
        )

    return detections, context_features, reference_points


def main() -> int:
    """Execute study-area feasibility CLI harness."""
    parser = argparse.ArgumentParser(
        description="SIH26162 DATA-001 Study-Area Feasibility Assessment Runner"
    )
    parser.add_argument(
        "--area-id",
        type=str,
        default=None,
        help="Specific candidate area_id (evaluates all if omitted).",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output report format (default: markdown).",
    )
    args = parser.parse_args()

    config = ScientificConfig(
        version="v1.0-data001-runner",
        name="feasibility_profile",
        description="Feasibility evaluation profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=30.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )

    detections, context_features, reference_points = (
        _generate_synthetic_benchmark_fixtures()
    )

    if args.area_id:
        area = get_candidate_study_area(args.area_id)
        assessment = evaluate_study_area_feasibility(
            study_area=area,
            detections=detections,
            context_features=context_features,
            reference_points=reference_points,
            config=config,
        )
        if args.format == "json":
            print(assessment.model_dump_json(indent=2))
        else:
            print(f"# Assessment for {area.name}")
            print(f"- Data Adequacy Score: {assessment.data_adequacy_score}")
            print(f"- Feasibility Level: {assessment.overall_feasibility.value}")
            print(f"- Recommended Role: {assessment.recommended_role.value}")
    else:
        report = run_comparative_feasibility_harness(
            study_areas=PROVISIONAL_CANDIDATE_AREAS,
            detections=detections,
            context_features=context_features,
            reference_points=reference_points,
            config=config,
        )
        if args.format == "json":
            print(report.model_dump_json(indent=2))
        else:
            md = generate_markdown_feasibility_report(report)
            print(md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
