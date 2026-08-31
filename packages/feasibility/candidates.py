"""Provisional candidate Indian study area definitions for feasibility evaluation.

CRITICAL ARCHITECTURAL INVARIANT:
These study areas are explicitly marked as PROVISIONAL CANDIDATES.
The final benchmark geography is NOT frozen at this stage.
"""

from packages.feasibility.models import StudyArea, StudyAreaRole
from packages.schemas.common import BoundingBox

JAMNAGAR_KUTCH = StudyArea(
    area_id="jamnagar_kutch",
    name="Jamnagar & Gulf of Kutch Refining and Petrochemical Corridor",
    state="Gujarat",
    bounding_box=BoundingBox(
        min_latitude=22.0,
        min_longitude=69.5,
        max_latitude=23.0,
        max_longitude=70.8,
    ),
    approx_area_sqkm=13900.0,
    description=(
        "World's largest petroleum refining and petrochemical complex "
        "including Reliance Jamnagar Refinery and Nayara Vadinar, surrounded "
        "by coastal ports, power plants, and salt marshes."
    ),
    scientific_rationale=(
        "Dense persistent industrial flaring and high-temperature thermal "
        "infrastructure with high-quality OSM feature tagging. Ideal for "
        "validating flare and persistent industrial thermal source tracking."
    ),
    is_provisional=True,
)

SINGRAULI_SONBHADRA = StudyArea(
    area_id="singrauli_sonbhadra",
    name="Singrauli & Sonbhadra Energy & Heavy Metallurgy Hub",
    state="Madhya Pradesh / Uttar Pradesh",
    bounding_box=BoundingBox(
        min_latitude=23.8,
        min_longitude=82.3,
        max_latitude=24.5,
        max_longitude=83.2,
    ),
    approx_area_sqkm=7150.0,
    description=(
        "India's energy capital featuring massive super thermal power stations "
        "(NTPC Singrauli, Vindhyachal, Rihand, Anpara), Northern Coalfields "
        "open-cast mines, aluminium smelting, and deciduous forest reserves."
    ),
    scientific_rationale=(
        "High density of both continuous heavy industrial thermal sources and "
        "seasonal natural forest fires, enabling multi-source segregation "
        "testing in complex terrain."
    ),
    is_provisional=True,
)

ANGUL_TALCHER = StudyArea(
    area_id="angul_talcher",
    name="Angul - Talcher Mining & Industrial Metallurgy Corridor",
    state="Odisha",
    bounding_box=BoundingBox(
        min_latitude=20.7,
        min_longitude=84.8,
        max_latitude=21.8,
        max_longitude=85.6,
    ),
    approx_area_sqkm=9800.0,
    description=(
        "Major industrial cluster comprising integrated steel manufacturing "
        "(Jindal Steel & Power), NALCO aluminium smelting, NTPC Talcher super "
        "thermal power, and extensive coal fields."
    ),
    scientific_rationale=(
        "Strong metallurgical and coal thermal footprint adjacent to dense "
        "Eastern Ghats forests for industrial-versus-wildfire discrimination."
    ),
    is_provisional=True,
)

PUNJAB_AGRICULTURAL = StudyArea(
    area_id="punjab_agricultural",
    name="Ludhiana - Sangrur - Patiala Crop Residue Burning Belt",
    state="Punjab",
    bounding_box=BoundingBox(
        min_latitude=30.0,
        min_longitude=75.2,
        max_latitude=31.0,
        max_longitude=76.5,
    ),
    approx_area_sqkm=13700.0,
    description=(
        "Intensive agricultural landscape characterized by acute, seasonal "
        "post-harvest stubble burning (paddy residue in Oct-Nov, wheat in "
        "Apr-May) with negligible heavy industrial flaring."
    ),
    scientific_rationale=(
        "Essential contrast and negative control region to ensure the system "
        "accurately identifies transient open agricultural burns without "
        "false industrial attribution."
    ),
    is_provisional=True,
)

# Global Calibration and Validation Corridors
PERSIAN_GULF_FLARING = StudyArea(
    area_id="persian_gulf",
    name="Persian Gulf Upstream/Downstream Petroleum Flaring Corridor",
    country="Saudi Arabia / UAE / Qatar",
    state="Gulf Coast",
    role=StudyAreaRole.SECONDARY_VALIDATION,
    bounding_box=BoundingBox(
        min_latitude=24.0,
        min_longitude=48.0,
        max_latitude=28.5,
        max_longitude=54.0,
    ),
    approx_area_sqkm=240000.0,
    description="Dense offshore and onshore continuous natural gas and petroleum flaring infrastructure.",
    scientific_rationale="Continuous mega-scale industrial thermal signatures in arid terrain for global model calibration.",
    is_provisional=True,
)

NORTH_AMERICA_CALIFORNIA = StudyArea(
    area_id="california_wui",
    name="California Wildland-Urban Interface & Sierra Forest Fire Corridor",
    country="United States",
    state="California",
    role=StudyAreaRole.CONTRAST_NEGATIVE_CONTROL,
    bounding_box=BoundingBox(
        min_latitude=34.0,
        min_longitude=-122.0,
        max_latitude=40.0,
        max_longitude=-118.0,
    ),
    approx_area_sqkm=200000.0,
    description="High-intensity summer/autumn forest and chaparral wildfires in complex mountainous terrain.",
    scientific_rationale="High-energy natural wildfire benchmarks with rigorous CalFire / MTBS ground truth.",
    is_provisional=True,
)

SOUTH_AMERICA_AMAZON = StudyArea(
    area_id="amazon_basin",
    name="Amazon Basin Deforestation and Agricultural Burning Corridor",
    country="Brazil",
    state="Mato Grosso / Para",
    role=StudyAreaRole.CONTRAST_NEGATIVE_CONTROL,
    bounding_box=BoundingBox(
        min_latitude=-14.0,
        min_longitude=-62.0,
        max_latitude=-8.0,
        max_longitude=-52.0,
    ),
    approx_area_sqkm=500000.0,
    description="Large-scale seasonal agricultural clearing and tropical forest margin fires.",
    scientific_rationale="Dense tropical non-industrial burning signatures with INPE ground truth registries.",
    is_provisional=True,
)

AUSTRALIA_SOUTHEAST = StudyArea(
    area_id="australia_southeast",
    name="Southeast Australia Eucalyptus & Bushfire Corridor",
    country="Australia",
    state="New South Wales / Victoria",
    role=StudyAreaRole.CONTRAST_NEGATIVE_CONTROL,
    bounding_box=BoundingBox(
        min_latitude=-38.0,
        min_longitude=144.0,
        max_latitude=-32.0,
        max_longitude=152.0,
    ),
    approx_area_sqkm=300000.0,
    description="Extreme-rate pyrocumulonimbus and temperate forest bushfires.",
    scientific_rationale="Natural high-intensity non-industrial fire benchmarks under dry windy conditions.",
    is_provisional=True,
)

PROVISIONAL_CANDIDATE_AREAS: list[StudyArea] = [
    JAMNAGAR_KUTCH,
    SINGRAULI_SONBHADRA,
    ANGUL_TALCHER,
    PUNJAB_AGRICULTURAL,
]

GLOBAL_CANDIDATE_AREAS: list[StudyArea] = [
    PERSIAN_GULF_FLARING,
    NORTH_AMERICA_CALIFORNIA,
    SOUTH_AMERICA_AMAZON,
    AUSTRALIA_SOUTHEAST,
]

ALL_CANDIDATE_AREAS: list[StudyArea] = (
    PROVISIONAL_CANDIDATE_AREAS + GLOBAL_CANDIDATE_AREAS
)


def get_candidate_study_area(area_id: str) -> StudyArea:
    """Retrieve candidate study area by area_id."""
    for candidate in ALL_CANDIDATE_AREAS:
        if candidate.area_id == area_id:
            return candidate
    raise KeyError(f"Candidate study area '{area_id}' not found.")
