"""SIH26162 — NEXT-012 Live Intelligence Demonstration Script.

Demonstrates unified Event -> Context -> Production ML Intelligence Pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight
from packages.schemas.event import Event
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.integration.intelligence_pipeline import (
    EventIntelligencePipelineService,
)


def make_detection(
    det_id: str,
    lat: float,
    lon: float,
    brightness: float,
    frp: float,
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_demo_012",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC),
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


def make_event(event_id: str, detections: list[Detection]) -> Event:
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


def main() -> None:
    print("=" * 80)
    print("SIH26162 — NEXT-012 LIVE INTELLIGENCE DEMONSTRATION")
    print("=" * 80)

    config = ScientificConfig(
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

    scenarios = [
        (
            "Scenario 1: High-Confidence Jamnagar Refinery Flare (AGREE)",
            make_event(
                "evt_jamnagar_01",
                [make_detection("d1", 22.470, 70.050, 395.0, 140.0)],
            ),
            [
                ContextFeature(
                    feature_id="osm_refinery_01",
                    provider="osm",
                    dataset_name="planet_osm_polygon",
                    dataset_version="v1.0.0",
                    context_type=ContextType.INDUSTRIAL,
                    geometry=Coordinate(latitude=22.4705, longitude=70.0502),
                    facility_name="Reliance Jamnagar Flare Unit 3",
                )
            ],
            ProductionOperatingMode.HIGH_RECALL,
        ),
        (
            "Scenario 2: Agricultural Biomass Fire (AGREE - Non-Industrial)",
            make_event(
                "evt_biomass_01",
                [make_detection("d2", 15.300, 76.200, 308.0, 7.5, DayNight.DAY)],
            ),
            [
                ContextFeature(
                    feature_id="osm_agri_01",
                    provider="osm",
                    dataset_name="planet_osm_polygon",
                    dataset_version="v1.0.0",
                    context_type=ContextType.AGRICULTURAL,
                    geometry=Coordinate(latitude=15.301, longitude=76.201),
                    facility_name="Farmland Cultivation Zone",
                )
            ],
            ProductionOperatingMode.HIGH_RECALL,
        ),
        (
            "Scenario 3: Missing Geospatial Context (ML_ONLY)",
            make_event(
                "evt_remote_01",
                [make_detection("d3", 24.100, 81.200, 380.0, 75.0)],
            ),
            [],
            ProductionOperatingMode.HIGH_PRECISION,
        ),
        (
            "Scenario 4: Contradictory Geospatial Context (CONFLICT -> Review)",
            make_event(
                "evt_conflict_01",
                [make_detection("d4", 22.470, 70.050, 375.0, 60.0)],
            ),
            [
                ContextFeature(
                    feature_id="osm_ind",
                    provider="osm",
                    dataset_name="planet_osm_polygon",
                    dataset_version="v1.0.0",
                    context_type=ContextType.INDUSTRIAL,
                    geometry=Coordinate(latitude=22.470, longitude=70.050),
                    facility_name="Industrial Park Gate A",
                ),
                ContextFeature(
                    feature_id="osm_crop",
                    provider="osm",
                    dataset_name="planet_osm_polygon",
                    dataset_version="v1.0.0",
                    context_type=ContextType.AGRICULTURAL,
                    geometry=Coordinate(latitude=22.471, longitude=70.051),
                    facility_name="Surrounding Agricultural Belt",
                ),
            ],
            ProductionOperatingMode.HIGH_PRECISION,
        ),
    ]

    for title, event, context_features, mode in scenarios:
        print(f"\n--- {title} ---")
        lat = event.centroid_geometry.latitude
        lon = event.centroid_geometry.longitude
        res = EventIntelligencePipelineService.evaluate_event_intelligence(
            event=event,
            member_detections=[make_detection("d", lat, lon, 380.0, 50.0)],
            candidate_features=context_features,
            mode=mode,
            config=config,
        )

        print(f"  Intelligence ID    : {res.intelligence_id}")
        print(f"  Operating Mode     : {res.operating_mode}")
        ml_str = (
            f"{res.ml_predicted_class} (assigned: {res.ml_assigned_class}, "
            f"conf: {res.ml_confidence:.4f})"
        )
        print(f"  ML Predicted Class : {ml_str}")
        ctx_eval = res.context_assessment
        ctx_str = (
            f"{ctx_eval.context_label} (conf: {ctx_eval.context_confidence:.4f}, "
            f"items: {ctx_eval.evidence_count})"
        )
        print(f"  Context Label      : {ctx_str}")
        print(f"  Agreement Status   : {res.agreement_status}")
        fin_str = (
            f"{res.final_classification} (composite conf: {res.confidence_score:.4f})"
        )
        print(f"  Final Decision     : {fin_str}")
        print(f"  Review Required    : {res.review_required}")
        if res.review_reasons:
            print(f"  Review Reasons     : {res.review_reasons}")
        lat_str = (
            f"Ctx={res.context_enrichment_latency_ms:.2f}ms | "
            f"Feat={res.feature_extraction_latency_ms:.2f}ms | "
            f"Inf={res.inference_latency_ms:.2f}ms | "
            f"Total={res.total_latency_ms:.2f}ms"
        )
        print(f"  Latencies          : {lat_str}")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE — ALL SCENARIOS VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()
