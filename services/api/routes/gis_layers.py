"""FastAPI routes for 12 GIS Layers catalog and metadata (GIS-012)."""

from fastapi import APIRouter

router = APIRouter(tags=["gis-layers"])

GIS_LAYERS_CATALOG = [
    {
        "id": "nasa-firms-viirs",
        "name": "NASA FIRMS VIIRS Thermal Detections",
        "category": "thermal",
        "provider": "NASA LANCE / FIRMS",
        "geometry_type": "Point",
        "description": (
            "375m active thermal anomaly detections from Suomi-NPP and NOAA-20."
        ),
        "interpretation": (
            "Subpixel infrared radiative excess indicating active ground combustion."
        ),
        "limitations": "Cloud cover occlusion; 375m nadir pixel footprint.",
        "update_frequency": "Every 3 hours (orbit passes)",
        "provenance": "NASA EOSDIS LANCE NRT Data Stream",
    },
    {
        "id": "nasa-firms-live-api",
        "name": "NASA FIRMS Live API Stream",
        "category": "thermal",
        "provider": "NASA FIRMS REST API",
        "geometry_type": "Point",
        "description": "Real-time query ingestion stream from NASA FIRMS Area API.",
        "interpretation": "Most current unclustered raw thermal observations.",
        "limitations": "Requires live API map token; NRT latency ~3 hours.",
        "update_frequency": "Real-time on query",
        "provenance": "NASA FIRMS API Key Verified",
    },
    {
        "id": "india-industrial-facilities",
        "name": "Master India Industrial Facilities",
        "category": "infrastructure",
        "provider": "OpenStreetMap & CPCB Registry",
        "geometry_type": "Polygon / Point",
        "description": (
            "Registry of refineries, petrochemicals, and heavy industry."
        ),
        "interpretation": "Ground infrastructure perimeters for proximity analysis.",
        "limitations": "Proximity indicates spatial correlation, NOT causation.",
        "update_frequency": "Curated Annual / Monthly",
        "provenance": "CPCB India & OpenStreetMap Contributors",
    },
    {
        "id": "global-power-plants",
        "name": "Global Power Plants Database",
        "category": "infrastructure",
        "provider": "World Resources Institute (WRI)",
        "geometry_type": "Point",
        "description": (
            "Thermal power generation facilities across India (Coal, Gas, Oil)."
        ),
        "interpretation": "Power generation thermal baseline locations.",
        "limitations": (
            "Point centroids; does not delineate precise perimeter geometry."
        ),
        "update_frequency": "Annual WRI Release",
        "provenance": "World Resources Institute v1.3.0",
    },
    {
        "id": "global-oil-gas-tracker",
        "name": "Global Oil & Gas Plant Tracker (GOGPT)",
        "category": "infrastructure",
        "provider": "Global Energy Monitor (GEM)",
        "geometry_type": "Point",
        "description": "Oil & gas extraction, refining, and LNG terminals.",
        "interpretation": (
            "Hydrocarbon processing plants subject to operational flaring."
        ),
        "limitations": "Commercial updates may lag new infrastructure commissioning.",
        "update_frequency": "Semi-annual GEM Release",
        "provenance": "Global Energy Monitor (GEM)",
    },
    {
        "id": "global-iron-steel-tracker",
        "name": "Global Iron & Steel Plant Tracker",
        "category": "infrastructure",
        "provider": "Global Energy Monitor (GEM)",
        "geometry_type": "Point",
        "description": (
            "Blast furnace, DRI, and electric arc metallurgy facilities in India."
        ),
        "interpretation": "High-temperature furnace tapping thermal sources.",
        "limitations": "Operational status changes require periodic verification.",
        "update_frequency": "Annual GEM Release",
        "provenance": "Global Energy Monitor (GEM)",
    },
    {
        "id": "cameo-niosh-hazmat",
        "name": "CAMEO-NIOSH Chemical Hazard Registry",
        "category": "hazard",
        "provider": "NOAA CAMEO / NIOSH Pocket Guide",
        "geometry_type": "Attribute / Table",
        "description": "Chemical toxicity, UN/NA numbers, and ERG isolation corridors.",
        "interpretation": "Toxic dispersion and firefighting protocol guidance.",
        "limitations": (
            "Facility chemical inventory represents typical industry baselines."
        ),
        "update_frequency": "ERG 2024 / NIOSH 2026",
        "provenance": "NOAA Office of Response and Restoration & NIOSH",
    },
    {
        "id": "historical-disasters",
        "name": "Historical Industrial Disasters Benchmark",
        "category": "benchmark",
        "provider": "Disaster Intelligence Archive",
        "geometry_type": "Point / Envelope",
        "description": (
            "Benchmark archive of notable Indian industrial fires and gas leaks."
        ),
        "interpretation": "Model validation and catastrophic accident calibration.",
        "limitations": "Historical case studies with retrospective satellite records.",
        "update_frequency": "Curated Research Benchmark",
        "provenance": "NDMA / State Disaster Management Reports",
    },
    {
        "id": "india-emergency-services",
        "name": "India Emergency Services & Mutual Aid Registry",
        "category": "responders",
        "provider": "National Disaster Response Directory",
        "geometry_type": "Point",
        "description": "Fire brigades, apex burn ICUs, and NDRF battalions.",
        "interpretation": (
            "Emergency resource proximity, modeled ETA, and contact directory."
        ),
        "limitations": "Road routing ETA may vary with traffic and weather conditions.",
        "update_frequency": "Quarterly National Sync",
        "provenance": "National Emergency Responder Database",
    },
    {
        "id": "multimodal-benchmark",
        "name": "Multimodal Validation Benchmark",
        "category": "benchmark",
        "provider": "SIH26162 Research Team",
        "geometry_type": "Point",
        "description": "Calibrated Tier A, B, and C ground-truth reference dataset.",
        "interpretation": (
            "Scientific ground-truth standard for ML precision and recall."
        ),
        "limitations": "Frozen benchmark split strictly isolated to prevent leakage.",
        "update_frequency": "Model Validation Cycle",
        "provenance": "SIH26162 Ground-Truth Engine",
    },
    {
        "id": "india-boundaries",
        "name": "India State & District Administrative Boundaries",
        "category": "geospatial",
        "provider": "Survey of India / Open Data",
        "geometry_type": "Polygon",
        "description": "WGS-84 state and district administrative jurisdictions.",
        "interpretation": "Administrative regional boundary clipping.",
        "limitations": "Generalized administrative coastline and boundaries.",
        "update_frequency": "Annual Survey of India Sync",
        "provenance": "Survey of India Open Series",
    },
    {
        "id": "indian-forest-reserves",
        "name": "Indian Forest Reserves & Protected Wilderness",
        "category": "environment",
        "provider": "Forest Survey of India (FSI)",
        "geometry_type": "Polygon / Point",
        "description": (
            "Protected tiger reserves and forest tracts for wildfire discrimination."
        ),
        "interpretation": (
            "Vegetation and canopy biomass thermal anomaly classification."
        ),
        "limitations": "Seasonal deciduous leaf-off variations influence fuel load.",
        "update_frequency": "Biennial FSI State of Forest Report",
        "provenance": "Forest Survey of India (FSI)",
    },
]


@router.get(
    "/api/gis-layers/metadata",
    operation_id="get_gis_layers_metadata",
    summary="Retrieve catalog and provenance metadata for all 12 GIS layers",
    description=(
        "Returns full metadata, source provenance, interpretation guidance, "
        "and limitations for each GIS layer."
    ),
)
def get_gis_layers_metadata() -> list[dict]:
    """Retrieve catalog and provenance metadata for all 12 GIS layers."""
    return GIS_LAYERS_CATALOG
