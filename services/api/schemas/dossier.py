"""FastAPI schemas for Tactical Incident Dossiers (DOSSIER-001)."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.responders import EmergencyResponder, ResponsePriority


class HazmatProfileInfo(BaseModel):
    """CAMEO-NIOSH hazardous chemical profile and isolation standards."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    facility_sector: str
    cameo_hazmat_class: str
    primary_chemicals: list[str]
    un_na_numbers: list[str]
    primary_disaster_risk: str
    initial_isolation_distance_meters: int
    downwind_evacuation_day_meters: int
    downwind_evacuation_night_meters: int
    toxic_combustion_byproducts: list[str]
    firefighting_protocol: str
    idlh_ppm: dict[str, str | int | float]


class PyrometryTelemetry(BaseModel):
    """Planck / Dozier dual-band pyrometry inversion results."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    emitter_temp_k: float
    emitter_area_m2: float
    background_temp_k: float
    radiance_residual: float
    is_valid: bool
    convergence_status: str


class PlumeTelemetry(BaseModel):
    """Gaussian dispersion plume and evacuation zone model."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    wind_speed_ms: float
    wind_direction_deg: float
    downwind_azimuth_deg: float
    plume_length_km: float
    plume_width_km: float
    evacuation_radius_km: float
    stability_class: str
    hazard_label: str
    plume_polygon_geojson: dict
    evacuation_circle_geojson: dict


class TacticalDossierResponse(BaseModel):
    """Comprehensive Tactical Incident Dossier for Emergency Response."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    dossier_id: str
    event_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    classification: str
    confidence: float
    uncertainty_state: str
    latitude: float
    longitude: float
    frp_mw: float
    detection_count: int
    started_at: datetime
    location_name: str
    facility_name: str | None
    facility_distance_meters: float | None
    facility_sector: str | None
    response_priority: ResponsePriority
    priority_reason: str
    hazmat: HazmatProfileInfo | None
    pyrometry: PyrometryTelemetry
    plume: PlumeTelemetry
    recommended_responders: list[EmergencyResponder]
    operational_recommendations: list[str]
    is_simulated_demo: bool = True
