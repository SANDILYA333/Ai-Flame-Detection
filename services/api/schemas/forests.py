"""Pydantic API schemas for Forest endpoints (Phase 1 / GIS-013)."""

from typing import Any

from pydantic import BaseModel, Field

from packages.schemas.common import Coordinate
from packages.schemas.forest import ForestType


class ForestDetailResponse(BaseModel):
    """Detailed response schema for a canonical single forest area."""

    id: str = Field(..., description="Canonical forest ID.")
    osm_id: int = Field(..., description="Raw OpenStreetMap ID.")
    osm_type: str = Field(..., description="OSM element type.")
    osm_identity: str = Field(..., description="Composite OSM identifier.")
    name: str | None = Field(None, description="Forest or reserve name.")
    name_en: str | None = Field(None, description="English name.")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 code.")
    region: str | None = Field(None, description="State / Region.")
    forest_type: ForestType = Field(..., description="Forest classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    area_km2: float = Field(..., description="Calculated area in square kilometers.")
    centroid: Coordinate = Field(..., description="Representative centroid coordinate.")
    geometry: dict[str, Any] = Field(..., description="GeoJSON polygon geometry.")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="OSM metadata tags."
    )
    source: str = Field(default="openstreetmap", description="Data source provenance.")
    is_repaired: bool = Field(
        default=False, description="Whether geometry was repaired."
    )


class NearbyForestItemResponse(BaseModel):
    """Single forest entry returned by nearby proximity search."""

    id: str = Field(..., description="Canonical forest ID.")
    osm_identity: str = Field(..., description="Composite OSM identifier.")
    name: str | None = Field(None, description="Forest name.")
    country_code: str = Field(..., description="ISO Country code.")
    forest_type: str = Field(..., description="Forest classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    distance_km: float = Field(
        ..., description="Geodesic distance to query location in km."
    )
    area_km2: float = Field(..., description="Forest area in km².")
    centroid: Coordinate = Field(..., description="Centroid coordinate.")


class NearbyForestsListResponse(BaseModel):
    """Response envelope for nearby forests search."""

    latitude: float = Field(..., description="Query point latitude.")
    longitude: float = Field(..., description="Query point longitude.")
    radius_km: float = Field(..., description="Search radius in kilometers.")
    total_found: int = Field(..., description="Total forests within radius.")
    forests: list[NearbyForestItemResponse] = Field(
        default_factory=list,
        description="Nearby forests ordered by ascending distance in km.",
    )


class BoundingBoxModel(BaseModel):
    """Geographic bounding box representation."""

    south: float = Field(..., description="South latitude bound in WGS-84 degrees.")
    west: float = Field(..., description="West longitude bound in WGS-84 degrees.")
    north: float = Field(..., description="North latitude bound in WGS-84 degrees.")
    east: float = Field(..., description="East longitude bound in WGS-84 degrees.")


class ForestIngestionRequest(BaseModel):
    """Request schema for triggering an OSM forest ingestion run."""

    south: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="South latitude bound in WGS-84 degrees [-90, 90].",
    )
    west: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="West longitude bound in WGS-84 degrees [-180, 180].",
    )
    north: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="North latitude bound in WGS-84 degrees [-90, 90].",
    )
    east: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="East longitude bound in WGS-84 degrees [-180, 180].",
    )
    min_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    min_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    max_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    max_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    country_code: str = Field(
        default="IN",
        description="Default ISO 3166-1 alpha-2 country code for the region.",
    )
    limit: int = Field(
        default=500,
        ge=1,
        le=2000,
        description="Maximum OSM elements to retrieve.",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, parse and validate without persisting to database.",
    )
    include_boundary: bool = Field(
        default=False,
        description="Whether to include boundary=forest tags.",
    )

    def get_resolved_bounds(self) -> tuple[float, float, float, float]:
        """Resolve (south, west, north, east) coordinates."""
        s = self.south if self.south is not None else self.min_lat
        w = self.west if self.west is not None else self.min_lon
        n = self.north if self.north is not None else self.max_lat
        e = self.east if self.east is not None else self.max_lon

        if s is None or w is None or n is None or e is None:
            raise ValueError(
                "Bounding box coordinates required: provide (south, west, north, east) "
                "or (min_lat, min_lon, max_lat, max_lon)."
            )

        if s > n:
            raise ValueError(
                f"Invalid latitude range: south ({s}) cannot exceed north ({n})."
            )

        lat_span = n - s
        lon_span = abs(e - w)
        max_span = 5.0
        max_area = 25.0

        if (
            lat_span > max_span
            or lon_span > max_span
            or (lat_span * lon_span) > max_area
        ):
            raise ValueError(
                f"Bounding box span ({lat_span:.2f}° x {lon_span:.2f}°) exceeds "
                f"safety limit of {max_span}° span / {max_area}° area. "
                "Query smaller regional bounding boxes to protect public Overpass API."
            )

        return s, w, n, e


class ForestIngestionResponse(BaseModel):
    """Response payload for administrative OSM forest ingestion."""

    success: bool = Field(
        default=True, description="Whether ingestion executed successfully."
    )
    source: str = Field(default="openstreetmap", description="Data source provenance.")
    bounding_box: BoundingBoxModel = Field(..., description="Geographic query bounds.")
    statistics: dict[str, Any] = Field(
        ..., description="Detailed ingestion telemetry statistics."
    )
    message: str = Field(
        default="Forest ingestion completed successfully.",
        description="Human-readable status message.",
    )


class NearbyForestThreatItemResponse(BaseModel):
    """Single forest item evaluated for proximity threat."""

    forest_id: str = Field(..., description="Canonical forest ID.")
    osm_identity: str = Field(..., description="OSM composite identifier.")
    name: str | None = Field(None, description="Forest or reserve name.")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code.")
    forest_type: str = Field(..., description="Forest classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    distance_km: float = Field(
        ..., description="Shortest geodesic distance to forest boundary in km."
    )
    inside_forest: bool = Field(
        default=False,
        description="True if fire coordinate lies inside the forest polygon.",
    )
    is_within_threat_radius: bool = Field(
        ..., description="True if distance <= configured threat radius."
    )
    threat_level: str = Field(
        ...,
        description="Assessed threat level classification.",
    )
    nearest_point: Coordinate | None = Field(
        None, description="Nearest coordinate on forest boundary."
    )
    centroid: Coordinate = Field(..., description="Forest centroid coordinate.")
    area_km2: float = Field(..., description="Forest area in km².")


class ThreatConfigurationModel(BaseModel):
    """Configured radius thresholds for threat evaluation."""

    search_radius_km: float = Field(..., description="Candidate search radius in km.")
    threat_radius_km: float = Field(..., description="Threat threshold in km.")
    awareness_radius_km: float = Field(
        default=10.0, description="Awareness threshold in km."
    )
    warning_radius_km: float = Field(
        default=5.0, description="Warning threshold in km."
    )
    critical_radius_km: float = Field(
        default=2.0, description="Critical threshold in km."
    )
    high_radius_km: float = Field(default=2.5, description="High threshold in km.")
    moderate_radius_km: float = Field(
        default=5.0, description="Moderate threshold in km."
    )


class ForestThreatAssessmentResponse(BaseModel):
    """Comprehensive spatial threat assessment response for a fire event."""

    success: bool = Field(default=True, description="Evaluation success.")
    fire_event_id: str | None = Field(
        None, description="FIRMS thermal event ID if evaluated from event."
    )
    fire_coordinate: Coordinate = Field(
        ..., description="Detected fire coordinate (lat, lon)."
    )
    configuration: ThreatConfigurationModel = Field(
        ..., description="Active radius configuration."
    )
    is_threatened: bool = Field(
        ..., description="True if any forest is within the threat radius."
    )
    threat_level: str = Field(
        ...,
        description="Assessed maximum forest threat level.",
    )
    nearest_forest: NearbyForestThreatItemResponse | None = Field(
        None, description="Closest forest area to the fire event."
    )
    nearby_forests: list[NearbyForestThreatItemResponse] = Field(
        default_factory=list,
        description="All forests within search radius, sorted by ascending distance.",
    )
    total_threatened_forests: int = Field(
        0, description="Count of forests within threat radius."
    )
    evaluated_at: str = Field(..., description="Evaluation timestamp in ISO-8601 UTC.")


class ForestProximityAlertRequest(BaseModel):
    """Payload to trigger or acknowledge a forest proximity alert."""

    event_id: str = Field(..., min_length=1, description="Canonical fire event ID.")
    forest_id: str = Field(
        ..., min_length=1, description="Target threatened forest ID."
    )
    fire_confidence: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Fire detection confidence percentage.",
    )
    recipient_phone: str | None = Field(
        default=None, description="Optional override responder phone number."
    )
    channels: list[str] = Field(
        default_factory=lambda: ["sms", "whatsapp"],
        description="Notification channels to dispatch.",
    )
    force_dispatch: bool = Field(
        default=False, description="Force notification dispatch even if already sent."
    )


class ForestProximityAlertResponse(BaseModel):
    """Response returned after evaluating a forest proximity alert."""

    success: bool = Field(default=True, description="Operation success indicator.")
    alert_id: str = Field(..., description="Unique deterministic alert ID.")
    event_id: str = Field(..., description="Canonical fire event ID.")
    forest_id: str = Field(..., description="Target forest ID.")
    forest_name: str | None = Field(None, description="Forest name.")
    distance_km: float = Field(..., description="Boundary distance in km.")
    inside_forest: bool = Field(..., description="True if fire is inside the forest.")
    threat_level: str = Field(..., description="Assessed threat level.")
    is_escalation: bool = Field(..., description="True if alert escalated severity.")
    notification_dispatched: bool = Field(
        ..., description="True if emergency notification was sent."
    )
    notification_id: str | None = Field(
        None, description="Notification dispatch ID if applicable."
    )
    created_at: str = Field(..., description="Alert creation ISO timestamp in UTC.")


class ForestThreatCandidateEventResponse(BaseModel):
    """Candidate thermal event threatening a forest."""

    event_id: str = Field(..., description="Canonical FIRMS thermal event ID.")
    coordinate: Coordinate = Field(..., description="Thermal event location.")
    distance_km: float = Field(..., description="Boundary distance in km.")
    inside_forest: bool = Field(default=False, description="True if inside forest.")
    threat_level: str = Field(..., description="Assessed threat level.")
    confidence: float = Field(..., description="Detection confidence %.")
    frp_mw: float = Field(..., description="Fire Radiative Power in MW.")
    classification: str = Field(default="UNKNOWN", description="Adjudicated class.")
    detected_at: str | None = Field(None, description="Observation ISO timestamp.")


class ForestThreatSummaryItemResponse(BaseModel):
    """Summarized threat intelligence item for a single forest."""

    forest_id: str = Field(..., description="Canonical forest ID.")
    osm_identity: str = Field(..., description="OSM composite identity.")
    name: str | None = Field(None, description="Forest or reserve name.")
    country_code: str = Field(..., description="ISO country code.")
    forest_type: str = Field(..., description="Forest category classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    area_km2: float = Field(..., description="Surface area in km².")
    centroid: Coordinate = Field(..., description="Centroid coordinate.")
    threat_level: str = Field(
        ..., description="Current operational threat state."
    )
    inside_forest: bool = Field(
        default=False, description="True if fire inside boundary."
    )
    primary_event_id: str | None = Field(
        None, description="Most severe fire ID."
    )
    primary_distance_km: float | None = Field(
        None, description="Distance to closest fire in km."
    )
    primary_confidence: float | None = Field(
        None, description="Fire confidence %."
    )
    primary_frp_mw: float | None = Field(
        None, description="Fire Radiative Power MW."
    )
    active_threat_count: int = Field(
        default=0, description="Count of threatening fires."
    )
    why_at_risk: list[str] = Field(
        default_factory=list, description="Explainability bullets."
    )
    progression_trend: str = Field(
        default="STATIONARY", description="Approach trend."
    )
    evaluated_at: str = Field(
        ..., description="Evaluation timestamp in ISO-8601 UTC."
    )


class GlobalForestMonitoringSummaryResponse(BaseModel):
    """Aggregated global KPI summary for monitored forests."""

    total_monitored_forests: int = Field(
        ..., description="Total monitored forests."
    )
    safe_forests: int = Field(..., description="Forests in SAFE status.")
    awareness_forests: int = Field(
        ..., description="Forests in AWARENESS state."
    )
    warning_forests: int = Field(..., description="Forests in WARNING state.")
    critical_forests: int = Field(..., description="Forests in CRITICAL state.")
    active_fire_forests: int = Field(
        ..., description="Forests with ACTIVE_FIRE."
    )
    total_threatened_forests: int = Field(
        ..., description="Total forests requiring action."
    )
    active_thermal_events_evaluated: int = Field(
        ..., description="Active fires evaluated."
    )
    evaluated_at: str = Field(
        ..., description="Evaluation timestamp in ISO-8601 UTC."
    )


class ForestMonitoringDashboardResponse(BaseModel):
    """Response payload for GET /forests/threats/monitoring."""

    success: bool = Field(default=True, description="Query success indicator.")
    summary: GlobalForestMonitoringSummaryResponse = Field(
        ..., description="Global KPIs."
    )
    total_filtered: int = Field(
        ..., description="Total forests matching active filter."
    )
    limit: int = Field(..., description="Page limit.")
    offset: int = Field(..., description="Page offset.")
    forests: list[ForestThreatSummaryItemResponse] = Field(
        default_factory=list, description="Ranked threatened forests."
    )


class ForestThreatDetailResponse(BaseModel):
    """Response payload for GET /forests/threats/forest/{forest_id}."""

    success: bool = Field(default=True, description="Query success indicator.")
    forest: ForestDetailResponse = Field(..., description="Full forest record.")
    threat_level: str = Field(..., description="Assessed threat level.")
    is_threatened: bool = Field(
        ..., description="True if within threat radius."
    )
    inside_forest: bool = Field(
        default=False, description="True if fire inside boundary."
    )
    nearest_event_id: str | None = Field(
        None, description="Closest fire event ID."
    )
    nearest_distance_km: float | None = Field(
        None, description="Distance to closest fire in km."
    )
    nearest_point: Coordinate | None = Field(
        None, description="Closest point on boundary."
    )
    primary_confidence: float | None = Field(
        None, description="Fire detection confidence %."
    )
    primary_frp_mw: float | None = Field(
        None, description="Fire Radiative Power MW."
    )
    threatening_events: list[ForestThreatCandidateEventResponse] = Field(
        default_factory=list, description="All threatening candidate fires."
    )
    why_at_risk: list[str] = Field(
        default_factory=list, description="Explainability bullets."
    )
    progression_trend: str = Field(
        default="STATIONARY", description="Approach trend."
    )
    evaluated_at: str = Field(
        ..., description="Evaluation timestamp in ISO-8601 UTC."
    )


