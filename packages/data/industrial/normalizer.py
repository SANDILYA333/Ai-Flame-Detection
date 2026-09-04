"""Deterministic normalization utilities for industrial infrastructure datasets."""

import hashlib
import math
import re
from typing import Any

from packages.schemas.enums import ContextType
from packages.schemas.industrial_asset import (
    AssetType,
    IndustryType,
    OperationalStatus,
)

# Standardized Indian States & Union Territories mapping
_INDIAN_STATES_MAP: dict[str, str] = {
    "andaman & nicobar islands": "Andaman and Nicobar",
    "andaman and nicobar": "Andaman and Nicobar",
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chandigarh": "Chandigarh",
    "chhattisgarh": "Chhattisgarh",
    "dadra & nagar haveli and daman & diu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "uttaranchal": "Uttarakhand",
    "west bengal": "West Bengal",
}


def normalize_facility_name(name: str | None) -> str:
    """Normalize and clean facility name while preserving acronyms."""
    if not name or not str(name).strip():
        return "Unknown Industrial Facility"

    clean = re.sub(r"\s+", " ", str(name).strip())
    # Clean leading/trailing quotes or brackets
    clean = clean.strip("\"' ")
    return clean if clean else "Unknown Industrial Facility"


def normalize_coordinates(lat_val: Any, lon_val: Any) -> tuple[float, float, bool]:
    """Validate and round decimal coordinates to 6 decimal places (~0.11m precision).

    Returns:
        tuple[float, float, bool]: (latitude, longitude, is_valid)
    """
    if lat_val is None or lon_val is None:
        return 0.0, 0.0, False

    try:
        lat = float(lat_val)
        lon = float(lon_val)
    except (ValueError, TypeError):
        return 0.0, 0.0, False

    if not (math.isfinite(lat) and math.isfinite(lon)):
        return 0.0, 0.0, False

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return 0.0, 0.0, False

    return round(lat, 6), round(lon, 6), True


def normalize_industry_and_asset_type(
    raw_type: str | None,
    raw_category: str | None = None,
    primary_fuel: str | None = None,
) -> tuple[IndustryType, AssetType, ContextType]:
    """Map provider strings to IndustryType, AssetType, and ContextType."""
    combined = f"{raw_type or ''} {raw_category or ''} {primary_fuel or ''}".lower()

    # 1. Solar Power
    if "solar" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_SOLAR, ContextType.POWER

    # 2. Coal Power
    if "coal" in combined or "lignite" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_COAL, ContextType.POWER

    # 3. Gas Power
    gas_tokens = ("power", "turbine", "gt", "ccpp", "ccgt")
    if "gas" in combined and any(w in combined for w in gas_tokens):
        return IndustryType.POWER, AssetType.POWER_PLANT_GAS, ContextType.POWER

    # 4. Hydro Power
    if "hydro" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_HYDRO, ContextType.POWER

    # 5. Wind Power
    if "wind" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_WIND, ContextType.POWER

    # 6. Nuclear Power
    if "nuclear" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_NUCLEAR, ContextType.POWER

    # 7. Biomass / Bioenergy Power
    if "biomass" in combined or "bioenergy" in combined or "bagasse" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_BIOMASS, ContextType.POWER

    # 8. Oil Power
    oil_tokens = ("oil power", "diesel power", "heavy fuel oil", "fuel oil")
    if any(w in combined for w in oil_tokens):
        return IndustryType.POWER, AssetType.POWER_PLANT_OIL, ContextType.POWER

    # 9. Steel & Metallurgy
    steel_tokens = (
        "steel",
        "metallurgy",
        "blast furnace",
        "bof",
        "eaf",
        "dri",
        "sponge iron",
    )
    if any(w in combined for w in steel_tokens):
        if "iron" in combined and "steel" not in combined:
            return (
                IndustryType.METALLURGY,
                AssetType.IRON_PLANT,
                ContextType.INDUSTRIAL,
            )
        return (
            IndustryType.METALLURGY,
            AssetType.STEEL_PLANT,
            ContextType.INDUSTRIAL,
        )

    # 10. Oil & Gas / Petrochemicals / Refining
    if any(w in combined for w in ("petrochemical", "polymer", "lng")):
        return (
            IndustryType.OIL_GAS,
            AssetType.PETROCHEMICAL_COMPLEX,
            ContextType.OIL_GAS,
        )

    if "refinery" in combined or "refining" in combined:
        return IndustryType.OIL_GAS, AssetType.REFINERY, ContextType.OIL_GAS

    if any(w in combined for w in ("oil & gas", "oil and gas", "flaring", "crude")):
        return (
            IndustryType.OIL_GAS,
            AssetType.PETROCHEMICAL_COMPLEX,
            ContextType.OIL_GAS,
        )

    # 11. General Power
    if "power" in combined or "thermal" in combined:
        return IndustryType.POWER, AssetType.POWER_PLANT_COAL, ContextType.POWER

    # 12. Mining
    if any(w in combined for w in ("mine", "quarry", "bauxite", "iron ore")):
        return IndustryType.MINING, AssetType.GENERAL_INDUSTRIAL, ContextType.MINING

    # 13. Default fallback
    return IndustryType.OTHER, AssetType.GENERAL_INDUSTRIAL, ContextType.INDUSTRIAL


def normalize_operational_status(status_str: str | None) -> OperationalStatus:
    """Normalize raw operational status strings into OperationalStatus enum."""
    if not status_str or not str(status_str).strip():
        return OperationalStatus.OPERATING

    val = str(status_str).strip().lower()

    if "operating" in val:
        return OperationalStatus.OPERATING
    if "construction" in val or "pre-construction" in val:
        return OperationalStatus.CONSTRUCTION
    if "announced" in val or "proposed" in val or "planning" in val:
        return OperationalStatus.ANNOUNCED
    if "retired" in val or "decommissioned" in val or "closed" in val:
        return OperationalStatus.RETIRED
    if "shelved" in val or "mothballed" in val or "idled" in val:
        return OperationalStatus.SHELVED
    if "cancel" in val:
        return OperationalStatus.CANCELLED

    return OperationalStatus.UNKNOWN


def normalize_state_name(state_str: str | None) -> str | None:
    """Normalize an Indian State or Union Territory name."""
    if not state_str or not str(state_str).strip():
        return None

    clean = re.sub(r"[^\w\s&]", "", str(state_str).strip().lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    return _INDIAN_STATES_MAP.get(clean, str(state_str).strip())


def compute_canonical_asset_id(
    provider: str,
    raw_id: str | None,
    name: str,
    latitude: float,
    longitude: float,
    primary_fuel: str | None = None,
) -> str:
    """Compute a deterministic canonical identifier for an industrial asset."""
    clean_prov = re.sub(r"[^a-zA-Z0-9]", "_", provider.strip().lower()).strip("_")

    if (
        raw_id
        and str(raw_id).strip()
        and str(raw_id).strip().lower() not in ("none", "nan", "null")
    ):
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(raw_id).strip())
        return f"ind_asset_{clean_prov}_{sanitized}"

    # Content-addressable hash fallback
    content_key = (
        f"{clean_prov}:"
        f"{name.strip().lower()}:"
        f"{round(latitude, 4)}:"
        f"{round(longitude, 4)}:"
        f"{str(primary_fuel or '').strip().lower()}"
    )
    raw_hash = hashlib.sha256(content_key.encode("utf-8")).hexdigest()
    return f"ind_asset_{clean_prov}_{raw_hash[:12]}"
