"""GeoJSON domain models for map layer endpoints (API-012, RFC 7946)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class GeoJsonGeometry(BaseModel):
    """Canonical RFC 7946 GeoJSON Geometry object."""

    type: str = Field(
        ...,
        description="GeoJSON geometry type (e.g. 'Point', 'Polygon', 'MultiPolygon').",
    )
    coordinates: Any = Field(
        ...,
        description="GeoJSON coordinates array in EPSG:4326 (WGS84 [lon, lat] order).",
    )


class GeoJsonFeature(BaseModel):
    """Canonical RFC 7946 GeoJSON Feature object."""

    type: Literal["Feature"] = "Feature"
    id: str | None = Field(
        default=None,
        description="Canonical unique feature identifier.",
    )
    geometry: GeoJsonGeometry = Field(
        ...,
        description="Geometry of the feature.",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value property payload associated with the feature.",
    )


class GeoJsonFeatureCollection(BaseModel):
    """Canonical RFC 7946 GeoJSON FeatureCollection container."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJsonFeature] = Field(
        default_factory=list,
        description="List of GeoJSON features in this layer.",
    )
    bbox: list[float] | None = Field(
        default=None,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat] in EPSG:4326.",
    )
