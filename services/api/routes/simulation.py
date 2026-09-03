"""FastAPI route for AI Simulation Lab and custom classification (SIM-001)."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from packages.physics.plume import GaussianPlumeEngine
from packages.physics.pyrometry import DozierPyrometrySolver
from services.ml.inference.production_runtime import ProductionMLRuntimeService

router = APIRouter(tags=["simulation"])


class CustomClassifyRequest(BaseModel):
    """Payload for custom thermal simulation and classification."""

    model_config = ConfigDict(extra="ignore")

    latitude: float = Field(default=22.4707, ge=-90.0, le=90.0)
    longitude: float = Field(default=70.0577, ge=-180.0, le=180.0)
    frp_mw: float = Field(default=75.0, ge=0.0)
    bright_mwir_k: float = Field(default=355.0, ge=200.0, le=500.0)
    bright_lwir_k: float = Field(default=298.0, ge=200.0, le=400.0)
    dist_to_facility_km: float = Field(default=0.4, ge=0.0)
    recurrence_90d: int = Field(default=8, ge=0)
    forest_fraction: float = Field(default=0.05, ge=0.0, le=1.0)
    cropland_fraction: float = Field(default=0.10, ge=0.0, le=1.0)
    wind_speed_ms: float = Field(default=4.2, ge=0.0)
    wind_direction_deg: float = Field(default=230.0, ge=0.0, le=360.0)


class CustomClassifyResponse(BaseModel):
    """Result returned by AI Simulation Lab."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    simulated_event_id: str
    predicted_class: str
    assigned_class: str
    confidence: float
    is_abstained: bool
    review_required: bool
    class_probabilities: dict[str, float]
    pyrometry: dict
    plume: dict
    xai_signals: list[dict]
    simulated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.post(
    "/api/classify",
    response_model=CustomClassifyResponse,
    operation_id="classify_simulated_event",
    summary="Execute real-time AI classification on simulated thermal inputs",
    description=(
        "Simulates a custom thermal observation, computes Planck pyrometry, "
        "Gaussian dispersion plume, and executes production ML inference."
    ),
)
@router.post(
    "/inference/simulate",
    response_model=CustomClassifyResponse,
    operation_id="classify_simulate_alias",
    summary="Alias for simulation classification",
    include_in_schema=False,
)
def classify_simulated_event(
    payload: CustomClassifyRequest,
) -> CustomClassifyResponse:
    """Execute real-time AI classification on simulated thermal inputs."""
    mwir_lwir_delta = payload.bright_mwir_k - payload.bright_lwir_k
    dist_meters = payload.dist_to_facility_km * 1000.0
    is_near_fac = dist_meters <= 1500.0
    is_persist = payload.recurrence_90d >= 4

    features = {
        "detection_count": max(1, payload.recurrence_90d),
        "frp_mean_mw": float(payload.frp_mw),
        "frp_max_mw": float(payload.frp_mw * 1.15),
        "frp_min_mw": float(payload.frp_mw * 0.85),
        "frp_sum_mw": float(payload.frp_mw * max(1, payload.recurrence_90d)),
        "frp_std_mw": float(payload.frp_mw * 0.15),
        "duration_hours": 3.5,
        "temporal_density": float(payload.recurrence_90d) / 3.5,
        "brightness_mean_kelvin": float(payload.bright_mwir_k),
        "brightness_max_kelvin": float(payload.bright_mwir_k + 5.0),
        "spatial_extent_radius_meters": 375.0,
        "daynight_ratio": 0.5,
        "satellite_platform_diversity": 2,
        "sensor_instrument": "VIIRS",
        "prior_event_count_24h": 1 if is_persist else 0,
        "prior_event_count_7d": min(7, payload.recurrence_90d),
        "prior_event_count_30d": min(30, payload.recurrence_90d * 2),
        "time_since_previous_event_hours": 12.0 if is_persist else 240.0,
        "persistence_active_days": payload.recurrence_90d,
        "persistence_total_events": payload.recurrence_90d * 2,
        "persistence_recurrence_ratio": (
            min(1.0, float(payload.recurrence_90d) / 30.0)
        ),
        "is_persistent_source": is_persist,
        "persistence_state": "CONFIRMED_PERSISTENT" if is_persist else "SPORADIC",
        "facility_distance_meters": dist_meters,
        "facility_context_type": (
            "PETROCHEMICAL" if is_near_fac else "RURAL_SETTLEMENT"
        ),
        "is_near_industrial_facility": is_near_fac,
        "power_plant_distance_meters": 12500.0,
        "landcover_class": (
            "FOREST"
            if payload.forest_fraction > 0.4
            else "CROPLAND"
            if payload.cropland_fraction > 0.4
            else "INDUSTRIAL_BUILTUP"
            if is_near_fac
            else "OPEN_LAND"
        ),
        "is_protected_area": payload.forest_fraction > 0.5,
        "water_distance_meters": 3200.0,
    }

    sim_id = f"SIM-EVT-{datetime.now(UTC).strftime('%H%M%S')}"
    ml_res = ProductionMLRuntimeService.predict_features(
        features=features,
        entity_id=sim_id,
    )

    pyro = DozierPyrometrySolver.solve(
        bright_mwir_k=payload.bright_mwir_k,
        bright_lwir_k=payload.bright_lwir_k,
        background_temp_k=295.0,
    )

    plume = GaussianPlumeEngine.compute_plume(
        latitude=payload.latitude,
        longitude=payload.longitude,
        frp_mw=payload.frp_mw,
        wind_speed_ms=payload.wind_speed_ms,
        wind_direction_deg=payload.wind_direction_deg,
    )

    fac_impact = (
        "supports_industrial"
        if payload.dist_to_facility_km < 1.0
        else "supports_non_industrial"
    )
    fac_weight = "+0.42" if payload.dist_to_facility_km < 1.0 else "-0.35"

    xai_signals = [
        {
            "feature": "dist_to_facility_km",
            "name": "Industrial Facility Proximity",
            "value": f"{payload.dist_to_facility_km:.2f} km",
            "impact": fac_impact,
            "weight": fac_weight,
        },
        {
            "feature": "mwir_lwir_delta",
            "name": "MWIR/LWIR Radiance Differential",
            "value": f"{mwir_lwir_delta:.1f} K",
            "impact": "supports_industrial" if mwir_lwir_delta > 35.0 else "neutral",
            "weight": "+0.31",
        },
        {
            "feature": "recurrence_90d",
            "name": "90-Day Longitudinal Recurrence",
            "value": f"{payload.recurrence_90d} active days",
            "impact": (
                "supports_industrial" if payload.recurrence_90d >= 4 else "neutral"
            ),
            "weight": "+0.28",
        },
        {
            "feature": "forest_fraction",
            "name": "Canopy & Forest Land-Cover",
            "value": f"{payload.forest_fraction * 100:.0f}%",
            "impact": (
                "supports_non_industrial"
                if payload.forest_fraction > 0.4
                else "neutral"
            ),
            "weight": "-0.15",
        },
    ]

    return CustomClassifyResponse(
        simulated_event_id=sim_id,
        predicted_class=ml_res.predicted_class,
        assigned_class=ml_res.assigned_class,
        confidence=ml_res.confidence,
        is_abstained=ml_res.is_abstained,
        review_required=ml_res.review_required,
        class_probabilities=ml_res.class_probabilities,
        pyrometry=pyro.to_dict(),
        plume=plume.to_dict(),
        xai_signals=xai_signals,
    )
