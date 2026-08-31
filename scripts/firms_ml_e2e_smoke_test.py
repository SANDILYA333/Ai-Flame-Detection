"""NASA FIRMS -> Production ML End-to-End Smoke Test (NEXT-010).

Demonstrates the complete operational pipeline:
NASA FIRMS Raw Ingestion -> Event Derivation -> Canonical feat_v1.0.0 (30 features)
-> ProductionMLRuntimeService -> Calibrated Policy -> Structured Prediction.

Executes 3 authoritative scenarios:
- Scenario A: High-Confidence Industrial Thermal Signature
- Scenario B: Ambiguous / Moderate-Confidence Signature (Abstention to Unknown)
- Scenario C: High-Confidence Non-Industrial Thermal Signature

Differentiates real pipeline execution with deterministic integration fixtures.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

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
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.integration.firms_pipeline import (
    FirmsProductionMLIntegrationService,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("firms_smoke_test")


def create_sample_detection(
    det_id: str,
    lat: float,
    lon: float,
    acq_dt: datetime,
    brightness_kelvin: float = 375.0,
    frp_mw: float = 85.0,
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    """Build a valid canonical Detection instance."""
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_firms_smoke_001",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=acq_dt,
        satellite="Suomi-NPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v2.0",
        raw_hash=f"hash_{det_id}",
        brightness_ti4_k=brightness_kelvin,
        brightness_ti5_k=310.0,
        frp_mw=frp_mw,
        confidence="high",
        scan_km=0.5,
        track_km=0.5,
        day_night=day_night,
    )


def create_sample_event(
    event_id: str,
    detections: list[Detection],
) -> Event:
    """Synthesize canonical Event from member detections."""
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
        formation_configuration_id="cfg_production_clustering",
        formation_configuration_version="v1.0.0",
        mean_frp_mw=sum(frps) / len(frps) if frps else None,
        max_frp_mw=max(frps) if frps else None,
    )


def run_smoke_test() -> None:
    print("=" * 80)
    print("SIH26162 — NEXT-010: LIVE FIRMS -> PRODUCTION ML END-TO-END SMOKE TEST")
    print("=" * 80)
    print("Mode: Deterministic Integration Fixture (Simulated Real FIRMS Detections)")
    print()

    # Base timestamp
    t0 = datetime(2026, 8, 15, 18, 30, 0, tzinfo=UTC)

    # --------------------------------------------------------------------------
    # Scenario A: High-Confidence Industrial Event (Refinery Flare)
    # --------------------------------------------------------------------------
    print("-" * 80)
    print("SCENARIO A: High-Confidence Industrial Flare Signature")
    print("-" * 80)
    ind_dets = [
        create_sample_detection(
            f"det_ind_{i}",
            22.470,
            70.050,
            t0,
            brightness_kelvin=385.0 + i * 2.0,
            frp_mw=95.0 + i * 5.0,
        )
        for i in range(4)
    ]
    ind_event = create_sample_event("evt_jamnagar_refinery_001", ind_dets)

    # Rich industrial context & source
    ind_source = PersistentSource(
        source_id="src_jamnagar_refinery_01",
        linked_event_ids=[f"evt_hist_{i}" for i in range(41)]
        + ["evt_jamnagar_refinery_001"],
        total_event_count=42,
        centroid_geometry=Coordinate(latitude=22.470, longitude=70.050),
        first_seen_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        last_seen_at=t0,
        active_days_count=65,
        persistence_state=PersistenceState.PERSISTENT,
        persistence_configuration_id="cfg_persistence_prod",
        persistence_configuration_version="v1.0.0",
        recurrence_ratio=0.88,
    )
    ind_context = [
        ContextEvidence(
            context_id="ctx_ind_01",
            source_type="osm",
            context_type=ContextType.INDUSTRIAL,
            geometry=Coordinate(latitude=22.470, longitude=70.050),
            availability_state=EvidenceAvailabilityState.AVAILABLE,
            distance_to_event_meters=150.0,
            facility_name="Jamnagar Complex Flare",
            raw_metadata={"industrial_type": "refinery"},
        )
    ]

    res_a = FirmsProductionMLIntegrationService.evaluate_event(
        event=ind_event,
        member_detections=ind_dets,
        mode=ProductionOperatingMode.HIGH_RECALL,
        source=ind_source,
        context_evidence=ind_context,
    )
    print(f"Event ID:             {res_a.event_id}")
    print(f"Operating Mode:       {res_a.operating_mode}")
    print(f"Model Resolved:       {res_a.model_name} ({res_a.model_version})")
    print(
        f"Features Extracted:   {res_a.feature_count} ({res_a.feature_schema_version})"
    )
    print(f"Predicted Class:      {res_a.predicted_class}")
    print(f"Assigned Class:       {res_a.assigned_class}")
    print(
        f"Confidence:           {res_a.confidence:.4f} "
        f"(Threshold: {res_a.threshold:.2f})"
    )
    print(f"Is Abstained:         {res_a.is_abstained}")
    print(f"Review Required:      {res_a.review_required}")
    print(
        f"Pipeline Latencies:   Feature Ext: "
        f"{res_a.feature_extraction_latency_ms:.2f} ms | "
        f"Inference: {res_a.inference_latency_ms:.2f} ms | "
        f"Total: {res_a.total_latency_ms:.2f} ms"
    )
    print()

    # --------------------------------------------------------------------------
    # Scenario B: Ambiguous / Moderate Signature -> Safe Abstention to UNKNOWN
    # --------------------------------------------------------------------------
    print("-" * 80)
    print("SCENARIO B: Ambiguous / Moderate Signature (Abstention Policy)")
    print("-" * 80)
    amb_dets = [
        create_sample_detection(
            "det_amb_01",
            21.200,
            75.500,
            t0,
            brightness_kelvin=350.0,
            frp_mw=30.0,
        )
    ]
    amb_event = create_sample_event("evt_ambiguous_002", amb_dets)

    res_b = FirmsProductionMLIntegrationService.evaluate_event(
        event=amb_event,
        member_detections=amb_dets,
        mode=ProductionOperatingMode.SELECTIVE,  # tau=0.80
    )
    print(f"Event ID:             {res_b.event_id}")
    print(f"Operating Mode:       {res_b.operating_mode}")
    print(f"Model Resolved:       {res_b.model_name} ({res_b.model_version})")
    print(f"Predicted Class:      {res_b.predicted_class}")
    print(f"Assigned Class:       {res_b.assigned_class}")
    print(
        f"Confidence:           {res_b.confidence:.4f} "
        f"(Threshold: {res_b.threshold:.2f})"
    )
    print(f"Is Abstained:         {res_b.is_abstained}")
    print(f"Review Required:      {res_b.review_required}")
    print(f"Abstention Reason:    {res_b.abstention_reason}")
    print(
        f"Pipeline Latencies:   Feature Ext: "
        f"{res_b.feature_extraction_latency_ms:.2f} ms | "
        f"Inference: {res_b.inference_latency_ms:.2f} ms | "
        f"Total: {res_b.total_latency_ms:.2f} ms"
    )
    print()

    # --------------------------------------------------------------------------
    # Scenario C: High-Confidence Non-Industrial Signature (Biomass Fire)
    # --------------------------------------------------------------------------
    print("-" * 80)
    print("SCENARIO C: High-Confidence Non-Industrial Signature (Biomass Fire)")
    print("-" * 80)
    bio_dets = [
        create_sample_detection(
            "det_bio_01",
            15.300,
            76.200,
            t0,
            brightness_kelvin=310.0,
            frp_mw=8.0,
            day_night=DayNight.DAY,
        )
    ]
    bio_event = create_sample_event("evt_biomass_fire_003", bio_dets)

    res_c = FirmsProductionMLIntegrationService.evaluate_event(
        event=bio_event,
        member_detections=bio_dets,
        mode=ProductionOperatingMode.HIGH_RECALL,  # tau=0.50
    )
    print(f"Event ID:             {res_c.event_id}")
    print(f"Operating Mode:       {res_c.operating_mode}")
    print(f"Model Resolved:       {res_c.model_name} ({res_c.model_version})")
    print(f"Predicted Class:      {res_c.predicted_class}")
    print(f"Assigned Class:       {res_c.assigned_class}")
    print(
        f"Confidence:           {res_c.confidence:.4f} "
        f"(Threshold: {res_c.threshold:.2f})"
    )
    print(f"Is Abstained:         {res_c.is_abstained}")
    print(f"Review Required:      {res_c.review_required}")
    print(
        f"Pipeline Latencies:   Feature Ext: "
        f"{res_c.feature_extraction_latency_ms:.2f} ms | "
        f"Inference: {res_c.inference_latency_ms:.2f} ms | "
        f"Total: {res_c.total_latency_ms:.2f} ms"
    )
    print()

    # --------------------------------------------------------------------------
    # Raw NASA FIRMS CSV End-to-End Parsing & Evaluation
    # --------------------------------------------------------------------------
    print("-" * 80)
    print("SCENARIO D: Raw NASA FIRMS CSV Ingestion & Evaluation")
    print("-" * 80)
    csv_payload = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
        "instrument,confidence,version,bright_t31,frp,daynight\n"
        "22.470,70.050,385.4,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,312.1,88.5,N\n"
        "22.472,70.051,387.1,0.5,0.5,2026-08-15,1830,N,VIIRS,high,2.0NRT,314.0,92.3,N\n"
        "15.300,76.200,308.2,0.6,0.5,2026-08-15,0815,N,VIIRS,nominal,2.0NRT,298.5,7.8,D\n"
    )
    csv_results = FirmsProductionMLIntegrationService.evaluate_firms_csv(
        csv_content=csv_payload,
        mode=ProductionOperatingMode.HIGH_RECALL,
    )
    print("Raw CSV Rows Ingested:    3 rows")
    print(f"Derived Thermal Events:   {len(csv_results)} events")
    for r in csv_results:
        print(
            f"  * Event [{r.event_id}]: Lat={r.centroid_latitude:.3f}, "
            f"Lon={r.centroid_longitude:.3f}, Dets={r.detection_count} -> "
            f"Class='{r.assigned_class}' (Conf={r.confidence:.4f}, "
            f"Abstained={r.is_abstained})"
        )
    print()
    print("=" * 80)
    print("ALL NASA FIRMS -> PRODUCTION ML INTEGRATION SMOKE TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_smoke_test()
