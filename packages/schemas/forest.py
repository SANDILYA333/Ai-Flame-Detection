"""Canonical domain schemas for global forest intelligence and OSM land cover.

Provides strongly-typed, validated domain models for forest areas, geometry
normalization, geospatial distance ordering, and ingestion telemetry.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel, Coordinate


class ForestType(StrEnum):
    """Canonical classification for forest and wooded land cover."""

    NATURAL_WOOD = "natural_wood"
    LANDUSE_FOREST = "landuse_forest"
    BOUNDARY_FOREST = "boundary_forest"
    PROTECTED_RESERVE = "protected_reserve"
    OTHER = "other"


class ForestGeometry(BaseDomainModel):
    """GeoJSON Polygon or MultiPolygon representation in EPSG:4326."""

    type: Literal["Polygon", "MultiPolygon"] = Field(
        ...,
        description="GeoJSON polygon geometry type.",
    )
    coordinates: list[Any] = Field(
        ...,
        description="Polygon rings [[[lon, lat], ...]] or MultiPolygon rings.",
    )


class ForestAreaRecord(BaseDomainModel):
    """Authoritative canonical forest area record normalized from OpenStreetMap."""

    forest_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical system identifier (e.g. 'forest_way_123456').",
    )
    osm_id: int = Field(
        ...,
        description="Raw OpenStreetMap object ID (e.g. 123456).",
    )
    osm_type: str = Field(
        ...,
        min_length=1,
        description="OpenStreetMap element type ('way' or 'relation').",
    )
    osm_identity: str = Field(
        ...,
        min_length=3,
        description="Composite OSM identifier ('way:123456' or 'relation:987654').",
    )
    name: str | None = Field(
        default=None,
        description="Primary name of the forest or reserve.",
    )
    name_en: str | None = Field(
        default=None,
        description="English name if available.",
    )
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=4,
        description="ISO 3166-1 alpha-2 country code (e.g. 'IN', 'BR', 'US').",
    )
    region: str | None = Field(
        default=None,
        description="State, province, or administrative region name.",
    )
    forest_type: ForestType = Field(
        ...,
        description="Canonical forest classification.",
    )
    osm_tag: str = Field(
        ...,
        description=(
            "Original defining OSM tag (e.g. 'natural=wood', 'landuse=forest')."
        ),
    )
    geometry: ForestGeometry = Field(
        ...,
        description="Authoritative boundary polygon/multipolygon geometry.",
    )
    centroid: Coordinate = Field(
        ...,
        description="Representative geographic centroid coordinate (EPSG:4326).",
    )
    area_km2: float = Field(
        ...,
        ge=0.0,
        description="Calculated surface area in square kilometers.",
    )
    metadata_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Preserved OSM key-value tags (e.g. leaf_type, operator).",
    )
    source: str = Field(
        default="openstreetmap",
        description="Data provenance source name.",
    )
    source_updated_at: datetime | None = Field(
        default=None,
        description="Timestamp of source OSM edit or changeset if available.",
    )
    is_repaired: bool = Field(
        default=False,
        description="True if geometry was non-simple/invalid and repaired safely.",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Record creation timestamp.",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Record last modification timestamp.",
    )

    @field_validator("country_code", mode="before")
    @classmethod
    def _normalize_country_code(cls, v: str) -> str:
        return v.strip().upper()


class NearbyForestItem(BaseDomainModel):
    """Item representing a forest proximate to a query location or fire event."""

    forest_id: str = Field(..., description="Unique canonical forest ID.")
    osm_identity: str = Field(..., description="OSM composite identity.")
    name: str | None = Field(None, description="Forest or reserve name.")
    country_code: str = Field(..., description="ISO-2 Country code.")
    forest_type: ForestType = Field(..., description="Classification.")
    osm_tag: str = Field(..., description="Original OSM tag.")
    distance_km: float = Field(
        ..., ge=0.0, description="Geodesic distance to query location in km."
    )
    area_km2: float = Field(..., ge=0.0, description="Surface area in km².")
    centroid: Coordinate = Field(..., description="Representative centroid coordinate.")


class NearbyForestsResponse(BaseDomainModel):
    """Response payload for nearby forest spatial proximity queries."""

    query_point: Coordinate = Field(..., description="Originating query coordinate.")
    radius_km: float = Field(..., ge=0.0, description="Search radius in kilometers.")
    total_found: int = Field(
        ..., ge=0, description="Number of matching forests within radius."
    )
    forests: list[NearbyForestItem] = Field(
        default_factory=list,
        description="Proximate forests ordered by ascending distance in km.",
    )


class ForestIngestionStats(BaseDomainModel):
    """Telemetry report summarizing results of an OSM forest ingestion run."""

    scope: str = Field(
        ..., description="Ingestion geographic target (e.g. 'country=IN' or bbox)."
    )
    source: str = Field(default="OPENSTREETMAP", description="Source name.")
    objects_received: int = Field(default=0, ge=0)
    polygons_parsed: int = Field(default=0, ge=0)
    invalid_geometries: int = Field(default=0, ge=0)
    geometry_repairs: int = Field(default=0, ge=0)
    inserted: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    duplicates_skipped: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    is_dry_run: bool = Field(default=False)
    duration_seconds: float = Field(default=0.0, ge=0.0)

    @property
    def fetched(self) -> int:
        """Alias for objects_received."""
        return self.objects_received

    @property
    def processed(self) -> int:
        """Alias for polygons_parsed."""
        return self.polygons_parsed

    @property
    def skipped(self) -> int:
        """Alias for duplicates_skipped."""
        return self.duplicates_skipped

    @property
    def failed(self) -> int:
        """Alias for invalid_geometries."""
        return self.invalid_geometries


class ForestThreatLevel(StrEnum):
    """Canonical threat level classification for fire-to-forest proximity."""

    ACTIVE_FIRE = "ACTIVE_FIRE"  # Fire inside/touching forest boundary (d = 0 km)
    INSIDE_FOREST = "INSIDE_FOREST"  # Alias for ACTIVE_FIRE
    CRITICAL = "CRITICAL"  # 0 km < Distance <= 2.0 km
    WARNING = "WARNING"  # 2.0 km < Distance <= 5.0 km
    AWARENESS = "AWARENESS"  # 5.0 km < Distance <= 10.0 km
    HIGH = "HIGH"  # Phase 3 alias (1.0 km < d <= 2.5 km)
    MODERATE = "MODERATE"  # Phase 3 alias (2.5 km < d <= 5.0 km)
    NONE = "NONE"  # Distance > awareness/search threshold
    SAFE = "SAFE"  # Alias for NONE (no active threat)
    LOW = "LOW"  # Legacy alias


class NearbyForestThreatItem(BaseDomainModel):
    """Forest area evaluated for proximity to a specific thermal fire event."""

    forest_id: str = Field(..., description="Unique canonical forest ID.")
    osm_identity: str = Field(..., description="OSM composite identity.")
    name: str | None = Field(None, description="Forest or reserve name.")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code.")
    forest_type: ForestType = Field(..., description="Forest classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    distance_km: float = Field(
        ..., ge=0.0, description="Shortest geodesic distance to forest boundary in km."
    )
    inside_forest: bool = Field(
        default=False,
        description="True if fire coordinate lies inside the forest polygon.",
    )
    is_within_threat_radius: bool = Field(
        ..., description="True if distance <= configured threat radius."
    )
    threat_level: ForestThreatLevel = Field(
        ..., description="Categorical threat classification based on distance."
    )
    nearest_point: Coordinate | None = Field(
        None, description="Closest point on forest boundary to the fire."
    )
    centroid: Coordinate = Field(..., description="Representative centroid coordinate.")
    area_km2: float = Field(..., ge=0.0, description="Surface area in km².")


class ForestThreatAssessment(BaseDomainModel):
    """Complete spatial threat intelligence assessment for a fire event."""

    fire_event_id: str | None = Field(
        None, description="Canonical FIRMS thermal event ID if evaluated from event."
    )
    fire_coordinate: Coordinate = Field(
        ..., description="WGS-84 coordinate of the detected fire location."
    )
    search_radius_km: float = Field(
        ..., ge=0.0, description="Configured candidate search radius in km."
    )
    threat_radius_km: float = Field(
        ..., ge=0.0, description="Configured proximity threat threshold in km."
    )
    awareness_radius_km: float = Field(
        10.0, ge=0.0, description="Threshold for AWARENESS threat level in km."
    )
    warning_radius_km: float = Field(
        5.0, ge=0.0, description="Threshold for WARNING threat level in km."
    )
    critical_radius_km: float = Field(
        2.0, ge=0.0, description="Threshold for CRITICAL threat level in km."
    )
    high_radius_km: float = Field(
        2.5, ge=0.0, description="Threshold for HIGH threat level in km."
    )
    moderate_radius_km: float = Field(
        5.0, ge=0.0, description="Threshold for MODERATE threat level in km."
    )
    is_threatened: bool = Field(
        ..., description="True if any forest is within the threat radius."
    )
    threat_level: ForestThreatLevel = Field(
        ..., description="Maximum threat level across all evaluated forests."
    )
    nearest_forest: NearbyForestThreatItem | None = Field(
        None, description="Closest forest area to the fire event."
    )
    nearby_forests: list[NearbyForestThreatItem] = Field(
        default_factory=list,
        description="All forests within search radius, sorted by ascending distance.",
    )
    total_threatened_forests: int = Field(
        0, ge=0, description="Count of forests within threat radius."
    )
    evaluated_at: datetime = Field(
        ..., description="Timestamp of threat evaluation in UTC."
    )


class ForestProximityAlertEvent(BaseDomainModel):
    """Canonical event payload when a thermal fire triggers a forest proximity alert."""

    alert_id: str = Field(
        ...,
        description="Unique deterministic alert identifier.",
    )
    event_id: str = Field(..., description="Canonical thermal fire event ID.")
    forest_id: str = Field(..., description="Target threatened forest ID.")
    forest_name: str | None = Field(None, description="Name of the threatened forest.")
    distance_km: float = Field(
        ..., ge=0.0, description="Shortest boundary distance in km."
    )
    inside_forest: bool = Field(
        default=False,
        description="True if fire is inside the forest boundary.",
    )
    threat_level: ForestThreatLevel = Field(
        ..., description="Assessed forest threat level."
    )
    fire_confidence: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Fire detection confidence percentage.",
    )
    fire_coordinate: Coordinate = Field(..., description="Fire coordinate (lat, lon).")
    created_at: datetime = Field(..., description="Alert creation timestamp in UTC.")
    is_escalation: bool = Field(
        default=False,
        description="True if alert escalated from a lower severity state.",
    )
    notification_dispatched: bool = Field(
        default=False,
        description="True if automated emergency notification was dispatched.",
    )
    notification_id: str | None = Field(
        default=None,
        description="Dispatched notification record ID if applicable.",
    )


class ForestThreatCandidateEvent(BaseDomainModel):
    """Candidate thermal event threatening a specific forest."""

    event_id: str = Field(..., description="Canonical FIRMS thermal event ID.")
    coordinate: Coordinate = Field(..., description="Thermal event location.")
    distance_km: float = Field(..., ge=0.0, description="Boundary distance in km.")
    inside_forest: bool = Field(default=False, description="True if inside forest.")
    threat_level: ForestThreatLevel = Field(..., description="Assessed threat level.")
    confidence: float = Field(
        ..., ge=0.0, le=100.0, description="Detection confidence %."
    )
    frp_mw: float = Field(..., ge=0.0, description="Fire Radiative Power in MW.")
    classification: str = Field(
        default="UNKNOWN", description="Predicted classification."
    )
    detected_at: datetime | None = Field(None, description="Observation timestamp.")


class ForestThreatSummaryItem(BaseDomainModel):
    """Aggregated operational threat summary for a single monitored forest."""

    forest_id: str = Field(..., description="Canonical forest ID.")
    osm_identity: str = Field(..., description="OSM composite identity.")
    name: str | None = Field(None, description="Forest or reserve name.")
    country_code: str = Field(..., description="ISO country code.")
    forest_type: ForestType = Field(..., description="Forest classification.")
    osm_tag: str = Field(..., description="Defining OSM tag.")
    area_km2: float = Field(..., ge=0.0, description="Surface area in km².")
    centroid: Coordinate = Field(..., description="Centroid coordinate.")
    threat_level: ForestThreatLevel = Field(
        ..., description="Current operational threat state."
    )
    inside_forest: bool = Field(
        default=False, description="True if fire is inside boundary."
    )
    primary_event_id: str | None = Field(
        None, description="Most severe/closest event ID."
    )
    primary_distance_km: float | None = Field(
        None, ge=0.0, description="Distance to closest fire in km."
    )
    primary_confidence: float | None = Field(
        None, ge=0.0, le=100.0, description="Fire confidence %."
    )
    primary_frp_mw: float | None = Field(
        None, ge=0.0, description="Fire Radiative Power MW."
    )
    active_threat_count: int = Field(
        default=0, ge=0, description="Count of threatening fires."
    )
    why_at_risk: list[str] = Field(
        default_factory=list, description="Structured explainability bullets."
    )
    progression_trend: str = Field(
        default="STATIONARY", description="Trend: APPROACHING, STATIONARY, etc."
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp in UTC.")


class GlobalForestMonitoringSummary(BaseDomainModel):
    """System-wide summary of monitored global forests and active threat counts."""

    total_monitored_forests: int = Field(
        ..., ge=0, description="Total monitored forests in system."
    )
    safe_forests: int = Field(..., ge=0, description="Forests with SAFE status.")
    awareness_forests: int = Field(
        ..., ge=0, description="Forests in AWARENESS state."
    )
    warning_forests: int = Field(..., ge=0, description="Forests in WARNING state.")
    critical_forests: int = Field(..., ge=0, description="Forests in CRITICAL state.")
    active_fire_forests: int = Field(
        ..., ge=0, description="Forests with ACTIVE_FIRE / interior fire."
    )
    total_threatened_forests: int = Field(
        ..., ge=0, description="Total forests requiring attention."
    )
    active_thermal_events_evaluated: int = Field(
        ..., ge=0, description="Total active thermal events checked."
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp in UTC.")


class ForestThreatDetail(BaseDomainModel):
    """Detailed threat intelligence report for a single monitored forest."""

    forest: ForestAreaRecord = Field(..., description="Canonical forest record.")
    threat_level: ForestThreatLevel = Field(..., description="Assessed threat level.")
    is_threatened: bool = Field(
        ..., description="True if any fire within threat radius."
    )
    inside_forest: bool = Field(
        default=False, description="True if fire inside forest."
    )
    nearest_event_id: str | None = Field(
        None, description="Closest thermal event ID."
    )
    nearest_distance_km: float | None = Field(
        None, ge=0.0, description="Shortest boundary distance."
    )
    nearest_point: Coordinate | None = Field(
        None, description="Closest coordinate on boundary."
    )
    primary_confidence: float | None = Field(
        None, description="Primary fire confidence %."
    )
    primary_frp_mw: float | None = Field(
        None, description="Primary fire FRP MW."
    )
    threatening_events: list[ForestThreatCandidateEvent] = Field(
        default_factory=list,
        description="All active thermal events within search radius.",
    )
    why_at_risk: list[str] = Field(
        default_factory=list, description="Explainable AI bullet points."
    )
    progression_trend: str = Field(
        default="STATIONARY", description="Threat progression trend."
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp in UTC.")


