"""Canonical domain schemas for normalized industrial infrastructure assets."""

import math
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel
from packages.schemas.enums import ContextType


class IndustryType(StrEnum):
    """Canonical industry classifications for industrial facilities."""

    POWER = "power"
    OIL_GAS = "oil_gas"
    METALLURGY = "metallurgy"
    CHEMICAL = "chemical"
    MANUFACTURING = "manufacturing"
    MINING = "mining"
    OTHER = "other"


class AssetType(StrEnum):
    """Specific asset type classifications for industrial facilities."""

    POWER_PLANT_SOLAR = "power_plant_solar"
    POWER_PLANT_COAL = "power_plant_coal"
    POWER_PLANT_GAS = "power_plant_gas"
    POWER_PLANT_HYDRO = "power_plant_hydro"
    POWER_PLANT_WIND = "power_plant_wind"
    POWER_PLANT_NUCLEAR = "power_plant_nuclear"
    POWER_PLANT_BIOMASS = "power_plant_biomass"
    POWER_PLANT_OIL = "power_plant_oil"
    REFINERY = "refinery"
    PETROCHEMICAL_COMPLEX = "petrochemical_complex"
    STEEL_PLANT = "steel_plant"
    IRON_PLANT = "iron_plant"
    GENERAL_INDUSTRIAL = "general_industrial"
    OTHER = "other"


class OperationalStatus(StrEnum):
    """Normalized operational status of an industrial asset."""

    OPERATING = "operating"
    CONSTRUCTION = "construction"
    ANNOUNCED = "announced"
    RETIRED = "retired"
    SHELVED = "shelved"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class DuplicateCandidate(BaseDomainModel):
    """Representation of a potential duplicate or co-located industrial facility."""

    primary_asset_id: str = Field(..., min_length=1)
    candidate_asset_id: str = Field(..., min_length=1)
    distance_meters: float = Field(..., ge=0.0)
    match_reasons: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class IndustrialAsset(BaseDomainModel):
    """Canonical normalized representation of an industrial facility.

    This model provides the spatial, operational, and attribution data foundation
    for map rendering, proximity analysis, and contextual fire attribution.
    """

    id: str = Field(
        ...,
        min_length=1,
        description=(
            "Deterministic canonical unique identifier "
            "(e.g. 'ind_asset_wri_WRI1020239')."
        ),
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Standardized human-readable facility name.",
    )
    asset_type: AssetType = Field(
        ...,
        description="Specific facility asset type classification.",
    )
    industry: IndustryType = Field(
        ...,
        description="Broad industry sector classification.",
    )
    context_type: ContextType = Field(
        ...,
        description=(
            "Canonical context classification compatible with SIH26162 taxonomy."
        ),
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Centroid latitude in WGS-84 decimal degrees (EPSG:4326).",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Centroid longitude in WGS-84 decimal degrees (EPSG:4326).",
    )
    country: str = Field(
        default="India",
        min_length=1,
        description="Country name or ISO-3 code.",
    )
    state: str | None = Field(
        None,
        description="Administrative State or Union Territory name.",
    )
    district: str | None = Field(
        None,
        description="District name if available.",
    )
    city: str | None = Field(
        None,
        description="City or municipality name if available.",
    )
    operator: str | None = Field(
        None,
        description="Operational company or facility operator.",
    )
    owner: str | None = Field(
        None,
        description="Owner entity or majority shareholder.",
    )
    status: OperationalStatus = Field(
        default=OperationalStatus.OPERATING,
        description="Current operational status.",
    )
    capacity: float | None = Field(
        None,
        ge=0.0,
        description="Numerical installed capacity value.",
    )
    capacity_unit: str | None = Field(
        None,
        description="Unit of capacity measurement (e.g. 'MW', 'ttpa').",
    )
    primary_fuel: str | None = Field(
        None,
        description="Primary fuel or energy source (e.g. 'Coal', 'Gas', 'Solar').",
    )
    commissioning_year: int | None = Field(
        None,
        ge=1800,
        le=2100,
        description="Year facility was commissioned or began operation.",
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Primary dataset or provider source name.",
    )
    source_id: str | None = Field(
        None,
        description=(
            "Raw identifier from provider (e.g. gppd_idnr, GEM unit ID)."
        ),
    )
    linked_source_ids: list[str] = Field(
        default_factory=list,
        description="Associated cross-source IDs or co-located unit IDs.",
    )
    is_map_eligible: bool = Field(
        default=True,
        description="Flag indicating if coordinates and quality allow map rendering.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved raw metadata attributes and URLs for lineage.",
    )

    @field_validator("latitude", "longitude", "capacity", mode="after")
    @classmethod
    def _validate_finite(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Coordinate and capacity measurements must be finite.")
        return v

    def to_geojson_feature(self, precision: int = 6) -> dict[str, Any]:
        """Serialize IndustrialAsset to an RFC 7946 GeoJSON Feature dictionary."""
        p_lat = round(self.latitude, precision)
        p_lon = round(self.longitude, precision)

        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {
                "type": "Point",
                "coordinates": [p_lon, p_lat],
            },
            "properties": {
                "id": self.id,
                "name": self.name,
                "asset_type": self.asset_type.value,
                "industry": self.industry.value,
                "context_type": self.context_type.value,
                "country": self.country,
                "state": self.state,
                "district": self.district,
                "city": self.city,
                "operator": self.operator,
                "owner": self.owner,
                "status": self.status.value,
                "capacity": self.capacity,
                "capacity_unit": self.capacity_unit,
                "primary_fuel": self.primary_fuel,
                "commissioning_year": self.commissioning_year,
                "source": self.source,
                "source_id": self.source_id,
                "linked_source_ids": self.linked_source_ids,
                "is_map_eligible": self.is_map_eligible,
                "metadata": self.metadata,
            },
        }


class IndustrialAssetCollection(BaseDomainModel):
    """Container collection for normalized industrial assets with summary statistics."""

    assets: list[IndustrialAsset] = Field(default_factory=list)
    total_count: int = Field(default=0, ge=0)
    map_eligible_count: int = Field(default=0, ge=0)
    sources_summary: dict[str, int] = Field(default_factory=dict)
    industries_summary: dict[str, int] = Field(default_factory=dict)
    duplicate_candidates_count: int = Field(default=0, ge=0)

    def to_geojson_feature_collection(self, precision: int = 6) -> dict[str, Any]:
        """Serialize the collection to an RFC 7946 GeoJSON FeatureCollection."""
        features = [
            a.to_geojson_feature(precision=precision)
            for a in self.assets
            if a.is_map_eligible
        ]
        bbox: list[float] | None = None
        if features:
            lons = [f["geometry"]["coordinates"][0] for f in features]
            lats = [f["geometry"]["coordinates"][1] for f in features]
            bbox = [
                round(min(lons), precision),
                round(min(lats), precision),
                round(max(lons), precision),
                round(max(lats), precision),
            ]

        fc: dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }
        if bbox is not None:
            fc["bbox"] = bbox
        return fc
