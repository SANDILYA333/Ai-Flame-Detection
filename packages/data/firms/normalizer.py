"""Field normalization, coordinate validation, timestamp parsing, and hashing."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from packages.data.firms.schemas import RawFirmsCsvRow
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight

# Regular expressions for date and time parsing
_DATE_REGEX = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_TIME_REGEX = re.compile(r"^(\d{1,2}):?(\d{2})$")


def parse_firms_timestamp(acq_date_str: str, acq_time_str: str) -> datetime:
    """Parse FIRMS acquisition date and time into an explicit UTC datetime.

    Args:
        acq_date_str: Date string in 'YYYY-MM-DD' format (e.g. '2026-08-01').
        acq_time_str: Time string in 'HHMM' or 'HH:MM' format.

    Returns:
        datetime: Timezone-aware UTC datetime.

    Raises:
        ValueError: If date or time format or calendar values are invalid.
    """
    clean_date = acq_date_str.strip()
    date_match = _DATE_REGEX.match(clean_date)
    if not date_match:
        raise ValueError(
            f"Invalid acq_date format '{acq_date_str}'. Expected 'YYYY-MM-DD'."
        )

    year = int(date_match.group(1))
    month = int(date_match.group(2))
    day = int(date_match.group(3))

    clean_time = acq_time_str.strip()
    # Normalize 3-digit time (e.g. '430' -> '0430')
    if len(clean_time) == 3 and clean_time.isdigit():
        clean_time = f"0{clean_time}"

    time_match = _TIME_REGEX.match(clean_time)
    if not time_match:
        raise ValueError(
            f"Invalid acq_time format '{acq_time_str}'. Expected 'HHMM' or 'HH:MM'."
        )

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))

    if not (0 <= hour <= 23):
        raise ValueError(
            f"Invalid hour '{hour}' in acq_time '{acq_time_str}'. Must be 0-23."
        )
    if not (0 <= minute <= 59):
        raise ValueError(
            f"Invalid minute '{minute}' in acq_time '{acq_time_str}'. Must be 0-59."
        )

    try:
        return datetime(year, month, day, hour, minute, 0, tzinfo=UTC)
    except ValueError as e:
        raise ValueError(f"Invalid calendar date '{acq_date_str}': {e}") from e


def normalize_satellite_name(raw_satellite: str, instrument: str | None = None) -> str:
    """Normalize raw FIRMS satellite identifier to canonical name.

    Args:
        raw_satellite: Raw satellite string from source (e.g. 'N', '1', 'T', 'A').
        instrument: Optional instrument name to disambiguate.

    Returns:
        str: Normalized canonical satellite name.
    """
    s = raw_satellite.strip().upper()

    mapping: dict[str, str] = {
        "N": "Suomi-NPP",
        "SNPP": "Suomi-NPP",
        "SUOMI-NPP": "Suomi-NPP",
        "NPP": "Suomi-NPP",
        "1": "NOAA-20",
        "N20": "NOAA-20",
        "NOAA-20": "NOAA-20",
        "NOAA20": "NOAA-20",
        "J1": "NOAA-20",
        "2": "NOAA-21",
        "N21": "NOAA-21",
        "NOAA-21": "NOAA-21",
        "NOAA21": "NOAA-21",
        "J2": "NOAA-21",
        "T": "Terra",
        "TERRA": "Terra",
        "A": "Aqua",
        "AQUA": "Aqua",
    }

    return mapping.get(s, raw_satellite.strip())


def normalize_instrument(raw_instrument: str | None, satellite: str) -> str:
    """Normalize instrument sensor name.

    Args:
        raw_instrument: Raw instrument name if provided.
        satellite: Normalized satellite name.

    Returns:
        str: Normalized sensor name ('VIIRS', 'MODIS', etc.).
    """
    if raw_instrument and raw_instrument.strip():
        inst = raw_instrument.strip().upper()
        if "VIIRS" in inst:
            return "VIIRS"
        if "MODIS" in inst:
            return "MODIS"
        return raw_instrument.strip()

    # Infer from normalized satellite
    sat = satellite.upper()
    if sat in ("TERRA", "AQUA"):
        return "MODIS"
    if sat in ("SUOMI-NPP", "NOAA-20", "NOAA-21"):
        return "VIIRS"

    return "UNKNOWN_SENSOR"


def normalize_day_night(raw_daynight: str | None) -> DayNight | None:
    """Normalize day/night indicator to canonical DayNight enum."""
    if not raw_daynight or not raw_daynight.strip():
        return None
    val = raw_daynight.strip().upper()
    if val in ("D", "DAY"):
        return DayNight.DAY
    if val in ("N", "NIGHT"):
        return DayNight.NIGHT
    return None


def compute_firms_raw_hash(raw_dict: dict[str, Any]) -> str:
    """Compute deterministic cryptographic SHA-256 hash of raw record dictionary.

    Args:
        raw_dict: Raw vendor row dictionary.

    Returns:
        str: 64-character lowercase hexadecimal SHA-256 hash.
    """
    # Create canonical sorted JSON representation
    normalized_dict: dict[str, Any] = {}
    for k in sorted(raw_dict.keys()):
        v = raw_dict[k]
        if v is None:
            normalized_dict[k] = None
        elif isinstance(v, str):
            normalized_dict[k] = v.strip()
        else:
            normalized_dict[k] = v

    canonical_json = json.dumps(
        normalized_dict, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_canonical_detection_id(source_snapshot_id: str, raw_hash: str) -> str:
    """Compute deterministic content-addressable detection identifier."""
    payload = f"{source_snapshot_id.strip()}:{raw_hash.strip()}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"det_{h}"


def normalize_raw_row_to_detection(
    row: RawFirmsCsvRow,
    raw_dict: dict[str, Any],
    source_snapshot_id: str,
    product_type: str = "nrt",
    product_version: str = "v2.0",
) -> Detection:
    """Normalize a validated raw FIRMS row into a canonical Detection domain object.

    Args:
        row: Validated RawFirmsCsvRow instance.
        raw_dict: Original raw row dictionary for provenance hashing.
        source_snapshot_id: Lineage identifier of originating source snapshot.
        product_type: Product tier (e.g. 'nrt', 'standard', 'urt').
        product_version: Processing version string.

    Returns:
        Detection: Canonical domain model.
    """
    # 1. Validate coordinates in WGS-84 (EPSG:4326)
    lat_v, lon_v = validate_wgs84_coordinates(row.latitude, row.longitude)
    geometry = Coordinate(latitude=lat_v, longitude=lon_v)

    # 2. Parse acquisition timestamp (UTC)
    acquired_at = parse_firms_timestamp(row.acq_date, row.acq_time)

    # 3. Normalize satellite and instrument
    satellite = normalize_satellite_name(row.satellite, row.instrument)
    instrument = normalize_instrument(row.instrument, satellite)

    # 4. Resolve brightness temperatures (VIIRS or MODIS aliases)
    brightness_ti4_k = row.bright_ti4 if row.bright_ti4 is not None else row.brightness
    brightness_ti5_k = row.bright_ti5 if row.bright_ti5 is not None else row.bright_t31

    # 5. Normalize day/night
    day_night = normalize_day_night(row.daynight)

    # 6. Product version fallback
    version_str = row.version.strip() if row.version else product_version

    # 7. Compute deterministic hashes
    raw_hash = compute_firms_raw_hash(raw_dict)
    detection_id = compute_canonical_detection_id(source_snapshot_id, raw_hash)

    return Detection(
        detection_id=detection_id,
        source="firms",
        source_snapshot_id=source_snapshot_id.strip(),
        acquired_at=acquired_at,
        geometry=geometry,
        satellite=satellite,
        instrument=instrument,
        product_type=product_type.strip(),
        product_version=version_str,
        raw_hash=raw_hash,
        frp_mw=row.frp,
        brightness_ti4_k=brightness_ti4_k,
        brightness_ti5_k=brightness_ti5_k,
        confidence=row.confidence.strip() if row.confidence else None,
        scan_km=row.scan,
        track_km=row.track,
        day_night=day_night,
    )
