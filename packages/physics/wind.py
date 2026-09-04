"""Meteorological wind conversions, directional geometry, and vector decomposition.

Enforces strict scientific conventions for atmospheric transport and dispersion:
- Meteorological Direction: Direction FROM which wind blows (measured clockwise from North).
- Downwind Azimuth: Direction TOWARD which wind transports plume/combustion mass.
- Cardinal Directions: 16-point compass resolution (N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW).
- Calm-Wind Handling: Flagged when wind speed < 0.5 m/s to prevent spurious plume dispersion vectors.
- Orthogonal Decomposed Components:
    u = -speed * sin(direction_from_rad)  (Eastward component)
    v = -speed * cos(direction_from_rad)  (Northward component)
"""

import math

from packages.schemas.weather import WindState, WindVector

_COMPASS_16_POINTS = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]

_COMPASS_8_POINTS = [
    "N", "NE", "E", "SE",
    "S", "SW", "W", "NW",
]


def normalize_degrees(degrees: float) -> float:
    """Normalize angular degree measure to the standard interval [0.0, 360.0).

    Args:
        degrees: Raw angle in decimal degrees.

    Returns:
        float: Normalized angle in [0.0, 360.0).
    """
    if not math.isfinite(degrees):
        raise ValueError(f"Angle must be a finite number, got {degrees}")
    normalized = degrees % 360.0
    if abs(normalized) < 1e-12 or abs(normalized - 360.0) < 1e-12:
        return 0.0
    return float(normalized)


def degrees_to_cardinal(degrees: float, points: int = 16) -> str:
    """Convert angular degree direction to a human-readable compass heading.

    Args:
        degrees: Angle in decimal degrees (0-360°).
        points: Compass resolution (16 for 16-point, 8 for 8-point).

    Returns:
        str: Compass bearing (e.g. 'N', 'NE', 'SSW').
    """
    norm_deg = normalize_degrees(degrees)
    if points == 8:
        step = 45.0
        index = int((norm_deg + (step / 2.0)) / step) % 8
        return _COMPASS_8_POINTS[index]

    step = 22.5
    index = int((norm_deg + (step / 2.0)) / step) % 16
    return _COMPASS_16_POINTS[index]


def classify_wind_state(speed_ms: float) -> WindState:
    """Classify wind speed into physical Beaufort-derived intensity states.

    Args:
        speed_ms: Wind speed in meters per second.

    Returns:
        WindState: Intensity category (CALM, LIGHT, MODERATE, FRESH, STRONG, GALE).
    """
    if not math.isfinite(speed_ms) or speed_ms < 0:
        raise ValueError(f"Wind speed must be a finite non-negative number, got {speed_ms}")

    if speed_ms < 0.5:
        return WindState.CALM
    if speed_ms <= 3.3:
        return WindState.LIGHT
    if speed_ms <= 7.9:
        return WindState.MODERATE
    if speed_ms <= 13.8:
        return WindState.FRESH
    if speed_ms <= 20.7:
        return WindState.STRONG
    return WindState.GALE


def compute_downwind_direction(direction_from_deg: float) -> float:
    """Calculate downwind direction (direction TO which wind blows).

    Downwind direction represents the transport trajectory of smoke plumes,
    firebrand dispersion, and thermal corridors.

    Formula:
        direction_to = (direction_from + 180) % 360

    Args:
        direction_from_deg: Meteorological wind direction FROM which wind originates (0-360°).

    Returns:
        float: Downwind direction in [0.0, 360.0).
    """
    norm_from = normalize_degrees(direction_from_deg)
    return normalize_degrees(norm_from + 180.0)


def compute_wind_vector_components(
    speed_ms: float, direction_from_deg: float
) -> tuple[float, float]:
    """Decompose wind speed and meteorological origin angle into orthogonal vector components.

    Orthogonal components follow WMO and geophysical standards:
    - u (zonal): Eastward positive velocity component (m/s)
    - v (meridional): Northward positive velocity component (m/s)

    For wind blowing FROM direction theta (measured clockwise from North):
        u = -speed * sin(theta_rad)
        v = -speed * cos(theta_rad)

    Args:
        speed_ms: Scalar wind speed in meters per second (>= 0).
        direction_from_deg: Meteorological direction FROM which wind blows in degrees.

    Returns:
        tuple[float, float]: (u_ms, v_ms) velocity components.
    """
    if not math.isfinite(speed_ms) or speed_ms < 0:
        raise ValueError(f"Wind speed must be a finite non-negative number, got {speed_ms}")

    norm_from = normalize_degrees(direction_from_deg)
    rad_from = math.radians(norm_from)

    u = -speed_ms * math.sin(rad_from)
    v = -speed_ms * math.cos(rad_from)

    # Clean small floating-point precision artifacts near zero
    if abs(u) < 1e-12:
        u = 0.0
    if abs(v) < 1e-12:
        v = 0.0

    return round(float(u), 4), round(float(v), 4)


def build_wind_vector(
    speed_ms: float,
    direction_from_deg: float,
    gust_ms: float | None = None,
    calm_threshold_ms: float = 0.5,
) -> WindVector:
    """Construct a validated WindVector canonical domain object with cardinal labels and calm detection.

    Args:
        speed_ms: Wind speed in m/s.
        direction_from_deg: Meteorological origin angle in degrees.
        gust_ms: Optional wind gust speed in m/s.
        calm_threshold_ms: Speed threshold below which wind is marked calm (default 0.5 m/s).

    Returns:
        WindVector: Fully calculated and validated wind vector domain record.
    """
    norm_from = normalize_degrees(direction_from_deg)
    dir_to = compute_downwind_direction(norm_from)
    from_label = degrees_to_cardinal(norm_from, points=16)
    to_label = degrees_to_cardinal(dir_to, points=16)
    u, v = compute_wind_vector_components(speed_ms, norm_from)
    is_calm = speed_ms < calm_threshold_ms
    state = classify_wind_state(speed_ms)

    valid_gust = None
    if gust_ms is not None:
        if not math.isfinite(gust_ms) or gust_ms < 0:
            raise ValueError(f"Wind gust must be a non-negative finite number, got {gust_ms}")
        valid_gust = round(float(gust_ms), 2)

    return WindVector(
        speed_ms=round(float(speed_ms), 2),
        direction_from_deg=round(norm_from, 2),
        direction_from_label=from_label,
        direction_to_deg=round(dir_to, 2),
        downwind_direction_label=to_label,
        gust_ms=valid_gust,
        u_ms=u,
        v_ms=v,
        is_calm=is_calm,
        wind_state=state,
    )
