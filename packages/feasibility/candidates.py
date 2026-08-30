"""Provisional candidate Indian study area definitions for feasibility evaluation.

CRITICAL ARCHITECTURAL INVARIANT:
These study areas are explicitly marked as PROVISIONAL CANDIDATES.
The final benchmark geography is NOT frozen at this stage.
"""

from packages.feasibility.models import StudyArea
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

PROVISIONAL_CANDIDATE_AREAS: list[StudyArea] = [
    JAMNAGAR_KUTCH,
    SINGRAULI_SONBHADRA,
    ANGUL_TALCHER,
    PUNJAB_AGRICULTURAL,
]


def get_candidate_study_area(area_id: str) -> StudyArea:
    """Retrieve provisional candidate study area by area_id."""
    for candidate in PROVISIONAL_CANDIDATE_AREAS:
        if candidate.area_id == area_id:
            return candidate
    raise KeyError(f"Candidate study area '{area_id}' not found.")
