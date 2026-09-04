"""Atmospheric Gaussian plume dispersion modeling and downwind hazard intelligence (Phase 3).

Implements Gaussian atmospheric dispersion with Briggs rural dispersion coefficients,
Pasquill-Gifford stability estimation, and multi-step downwind hazard sampling.

NOTICE: This model is an engineering approximation designed for rapid situational awareness
and hazard bounding; it does not constitute a certified regulatory toxicological prediction.
"""

import math
from datetime import datetime, timezone
from typing import Any

from packages.geospatial.coordinates import project_coordinate, validate_wgs84_coordinates
from packages.physics.wind import build_wind_vector, compute_downwind_direction
from packages.schemas.common import Coordinate
from packages.schemas.dispersion import (
    AtmosphericDispersionResult,
    DispersionSamplePoint,
    DispersionSummary,
    PasquillStabilityClass,
)
from packages.schemas.weather import DataQuality, WindVector


def estimate_pasquill_stability(
    wind_speed_ms: float,
    cloud_cover_pct: float | None = None,
    is_daytime: bool = True,
) -> tuple[PasquillStabilityClass, str]:
    """Estimate Pasquill-Gifford atmospheric stability class from available meteorology.

    Args:
        wind_speed_ms: Surface wind speed at 10m height (m/s).
        cloud_cover_pct: Cloud cover percentage (0-100%).
        is_daytime: Whether the observation epoch corresponds to daytime insolation.

    Returns:
        tuple[PasquillStabilityClass, str]: (stability_class, rationale_explanation).
    """
    speed = max(0.0, float(wind_speed_ms))
    cloud = 50.0 if cloud_cover_pct is None else max(0.0, min(100.0, float(cloud_cover_pct)))

    if is_daytime:
        if speed < 2.0:
            if cloud < 40.0:
                return PasquillStabilityClass.A, "Daytime, light wind (<2 m/s), low cloud cover -> Strong insolation -> Very Unstable (Class A)"
            if cloud < 75.0:
                return PasquillStabilityClass.B, "Daytime, light wind (<2 m/s), moderate cloud cover -> Moderate insolation -> Moderately Unstable (Class B)"
            return PasquillStabilityClass.C, "Daytime, light wind (<2 m/s), heavy overcast -> Slight insolation -> Slightly Unstable (Class C)"
        if speed <= 5.0:
            if cloud < 40.0:
                return PasquillStabilityClass.B, "Daytime, moderate wind (2-5 m/s), low cloud cover -> Moderate insolation -> Moderately Unstable (Class B)"
            if cloud < 75.0:
                return PasquillStabilityClass.C, "Daytime, moderate wind (2-5 m/s), moderate clouds -> Slight insolation -> Slightly Unstable (Class C)"
            return PasquillStabilityClass.D, "Daytime, moderate wind (2-5 m/s), heavy clouds -> Neutral (Class D)"
        return PasquillStabilityClass.D, f"Daytime, strong wind ({speed:.1f} m/s) -> Mechanically Neutral (Class D)"

    # Nighttime
    if speed < 2.0:
        if cloud < 50.0:
            return PasquillStabilityClass.F, "Nighttime, light wind (<2 m/s), clear skies -> Radiative cooling -> Moderately Stable (Class F)"
        return PasquillStabilityClass.E, "Nighttime, light wind (<2 m/s), overcast -> Slightly Stable (Class E)"
    if speed <= 5.0:
        if cloud < 50.0:
            return PasquillStabilityClass.E, "Nighttime, moderate wind (2-5 m/s), clear skies -> Slightly Stable (Class E)"
        return PasquillStabilityClass.D, "Nighttime, moderate wind (2-5 m/s), overcast -> Neutral (Class D)"
    return PasquillStabilityClass.D, f"Nighttime, strong wind ({speed:.1f} m/s) -> Mechanically Neutral (Class D)"


def compute_sigma_y(x_m: float, stability: PasquillStabilityClass) -> float:
    """Calculate horizontal crosswind dispersion standard deviation sigma_y (meters).

    Uses Briggs open-country dispersion parameterization.

    Args:
        x_m: Downwind distance in meters (>= 0).
        stability: Pasquill-Gifford stability class.

    Returns:
        float: sigma_y in meters (>= 1.0 m).
    """
    x = max(10.0, float(x_m))
    coeff_map = {
        PasquillStabilityClass.A: 0.22,
        PasquillStabilityClass.B: 0.16,
        PasquillStabilityClass.C: 0.11,
        PasquillStabilityClass.D: 0.08,
        PasquillStabilityClass.E: 0.06,
        PasquillStabilityClass.F: 0.04,
    }
    c_y = coeff_map.get(stability, 0.08)
    sigma_y = c_y * x * ((1.0 + 0.0001 * x) ** (-0.5))
    return max(1.0, float(sigma_y))


def compute_sigma_z(x_m: float, stability: PasquillStabilityClass) -> float:
    """Calculate vertical dispersion standard deviation sigma_z (meters).

    Uses Briggs open-country dispersion parameterization.

    Args:
        x_m: Downwind distance in meters (>= 0).
        stability: Pasquill-Gifford stability class.

    Returns:
        float: sigma_z in meters (>= 1.0 m).
    """
    x = max(10.0, float(x_m))
    if stability == PasquillStabilityClass.A:
        sigma_z = 0.20 * x
    elif stability == PasquillStabilityClass.B:
        sigma_z = 0.12 * x
    elif stability == PasquillStabilityClass.C:
        sigma_z = 0.08 * x * ((1.0 + 0.0002 * x) ** (-0.5))
    elif stability == PasquillStabilityClass.D:
        sigma_z = 0.06 * x * ((1.0 + 0.0015 * x) ** (-0.5))
    elif stability == PasquillStabilityClass.E:
        sigma_z = 0.03 * x * ((1.0 + 0.0003 * x) ** (-1.0))
    else:  # PasquillStabilityClass.F
        sigma_z = 0.016 * x * ((1.0 + 0.0003 * x) ** (-1.0))

    return max(1.0, float(sigma_z))


def compute_ground_concentration(
    q_strength: float,
    u_ms: float,
    x_m: float,
    y_m: float,
    h_release_m: float,
    stability: PasquillStabilityClass,
) -> float:
    """Calculate ground-level pollutant/heat concentration C(x, y, 0).

    Formula:
        C(x, y, 0) = (Q / (pi * u * sigma_y * sigma_z)) * exp(-y^2 / (2*sigma_y^2)) * exp(-H^2 / (2*sigma_z^2))

    Args:
        q_strength: Source emission strength proxy (>= 0).
        u_ms: Wind transport velocity in m/s (>= 0).
        x_m: Downwind distance in meters (> 0).
        y_m: Crosswind lateral distance in meters.
        h_release_m: Effective release height in meters.
        stability: Pasquill stability class.

    Returns:
        float: Ground-level relative concentration value.
    """
    if q_strength <= 0.0:
        return 0.0

    u_eff = max(0.5, float(u_ms))
    x = max(10.0, float(x_m))
    y = float(y_m)
    h = max(0.0, float(h_release_m))

    sig_y = compute_sigma_y(x, stability)
    sig_z = compute_sigma_z(x, stability)

    # Lateral decay term
    lat_term = math.exp(-0.5 * (y / sig_y) ** 2)

    # Vertical elevation decay term
    vert_term = math.exp(-0.5 * (h / sig_z) ** 2)

    denom = math.pi * u_eff * sig_y * sig_z
    if denom <= 0.0 or not math.isfinite(denom):
        return 0.0

    conc = (q_strength / denom) * lat_term * vert_term
    return max(0.0, float(conc))


class AtmosphericDispersionEngine:
    """Production Gaussian dispersion engine for calculating downwind hazard corridors."""

    MIN_DISTANCE_KM: float = 0.5
    MAX_DISTANCE_KM: float = 35.0
    SAMPLE_STEPS: int = 12

    @classmethod
    def evaluate_dispersion(
        cls,
        *,
        latitude: float,
        longitude: float,
        weather: Any = None,
        wind: WindVector | None = None,
        frp_mw: float | None = None,
        event_id: str | None = None,
        release_height_m: float | None = None,
        cloud_cover_pct: float | None = None,
        is_daytime: bool = True,
        max_distance_km: float | None = None,
        data_quality: DataQuality = DataQuality.LIVE,
    ) -> AtmosphericDispersionResult:
        """Alias for calculate_dispersion supporting flexible keyword arguments."""
        eff_wind = wind
        eff_cloud = cloud_cover_pct
        eff_quality = data_quality

        if weather is not None:
            eff_wind = weather.wind
            eff_cloud = weather.atmosphere.cloud_cover_pct
            eff_quality = weather.data_quality

        if eff_wind is None:
            eff_wind = build_wind_vector(speed_ms=5.0, direction_from_deg=270.0)

        return cls.calculate_dispersion(
            latitude=latitude,
            longitude=longitude,
            frp_mw=frp_mw or 50.0,
            wind=eff_wind,
            event_id=event_id,
            release_height_m=release_height_m,
            cloud_cover_pct=eff_cloud,
            is_daytime=is_daytime,
            max_distance_km=max_distance_km,
            data_quality=eff_quality,
        )

    @classmethod
    def calculate_dispersion(
        cls,
        latitude: float,
        longitude: float,
        frp_mw: float,
        wind: WindVector,
        event_id: str | None = None,
        release_height_m: float | None = None,
        cloud_cover_pct: float | None = None,
        is_daytime: bool = True,
        max_distance_km: float | None = None,
        data_quality: DataQuality = DataQuality.LIVE,
    ) -> AtmosphericDispersionResult:
        """Derive full downwind dispersion trajectory, lateral boundaries, and concentration profile.

        Args:
            latitude: Incident origin latitude.
            longitude: Incident origin longitude.
            frp_mw: Fire Radiative Power in MW (>= 0).
            wind: Normalized wind vector record from Phase 2.
            event_id: Optional thermal event identifier.
            release_height_m: Estimated physical release/stack height in meters.
            cloud_cover_pct: Atmospheric cloud cover percentage.
            is_daytime: Observation time of day.
            max_distance_km: Optional manual horizon limit override.
            data_quality: Ingested meteorological data quality.

        Returns:
            AtmosphericDispersionResult: Complete validated dispersion model.
        """
        valid_lat, valid_lon = validate_wgs84_coordinates(latitude, longitude)
        eff_frp = max(0.0, float(frp_mw))

        # Effective release height: use explicit value or calculate buoyant plume rise proxy
        if release_height_m is not None:
            eff_release_h = max(0.0, float(release_height_m))
        else:
            eff_release_h = min(150.0, 2.5 * math.sqrt(max(1.0, eff_frp)) + 5.0)

        # 1. Source strength proxy
        # Q is proportional to sqrt(max(FRP, 1.0))
        q_proxy = math.sqrt(max(1.0, eff_frp))

        # 2. Stability classification
        stability, rationale = estimate_pasquill_stability(
            wind_speed_ms=wind.speed_ms,
            cloud_cover_pct=cloud_cover_pct,
            is_daytime=is_daytime,
        )

        # 3. Downwind transport angle
        downwind_deg = wind.direction_to_deg
        u_eff = max(0.5, wind.speed_ms)

        # 4. Maximum hazard extent scaling
        if max_distance_km is not None:
            max_dist_km = max(cls.MIN_DISTANCE_KM, min(cls.MAX_DISTANCE_KM, float(max_distance_km)))
        else:
            stability_distance_multiplier = {
                PasquillStabilityClass.A: 0.75,
                PasquillStabilityClass.B: 0.85,
                PasquillStabilityClass.C: 0.95,
                PasquillStabilityClass.D: 1.00,
                PasquillStabilityClass.E: 1.15,
                PasquillStabilityClass.F: 1.30,
            }.get(stability, 1.0)

            raw_max_dist_km = (
                (math.sqrt(q_proxy) * 2.4 / (u_eff**0.35))
                * stability_distance_multiplier
            )
            max_dist_km = max(cls.MIN_DISTANCE_KM, min(cls.MAX_DISTANCE_KM, raw_max_dist_km))

        # 5. Generate discrete downwind trajectory samples
        sample_points: list[DispersionSamplePoint] = []
        raw_concentrations: list[float] = []

        # Distance distribution: denser near the source, expanding outward
        distances_km: list[float] = []
        for step in range(1, cls.SAMPLE_STEPS + 1):
            fraction = step / cls.SAMPLE_STEPS
            # Quadratic spacing for high near-source resolution
            d_km = round(fraction**1.4 * max_dist_km, 3)
            if d_km >= 0.05 and d_km not in distances_km:
                distances_km.append(d_km)

        # Ensure max_dist_km is the terminal step
        if distances_km and distances_km[-1] != max_dist_km:
            distances_km[-1] = round(max_dist_km, 3)

        max_lateral_width_km = 0.0
        calm_spread_multiplier = 1.6 if wind.is_calm else 1.0

        for d_km in distances_km:
            x_m = d_km * 1000.0
            sig_y = compute_sigma_y(x_m, stability) * calm_spread_multiplier
            sig_z = compute_sigma_z(x_m, stability)

            # Lateral half-width encompassing 90% of plume mass (approx. 2.15 sigma_y)
            half_width_km = (2.15 * sig_y) / 1000.0
            total_width_km = round(half_width_km * 2.0, 3)
            if total_width_km > max_lateral_width_km:
                max_lateral_width_km = total_width_km

            # Centerline geographic projection
            c_lat, c_lon = project_coordinate(valid_lat, valid_lon, d_km, downwind_deg)
            center_coord = Coordinate(latitude=c_lat, longitude=c_lon)

            # Left boundary projection (orthogonal left: downwind - 90°)
            left_bearing = (downwind_deg - 90.0) % 360.0
            l_lat, l_lon = project_coordinate(c_lat, c_lon, half_width_km, left_bearing)
            left_coord = Coordinate(latitude=l_lat, longitude=l_lon)

            # Right boundary projection (orthogonal right: downwind + 90°)
            right_bearing = (downwind_deg + 90.0) % 360.0
            r_lat, r_lon = project_coordinate(c_lat, c_lon, half_width_km, right_bearing)
            right_coord = Coordinate(latitude=r_lat, longitude=r_lon)

            # Centerline ground-level concentration
            conc_center = compute_ground_concentration(
                q_strength=q_proxy,
                u_ms=wind.speed_ms,
                x_m=x_m,
                y_m=0.0,
                h_release_m=eff_release_h,
                stability=stability,
            )
            raw_concentrations.append(conc_center)

            sample_points.append(
                DispersionSamplePoint(
                    downwind_distance_km=d_km,
                    centerline_point=center_coord,
                    left_boundary_point=left_coord,
                    right_boundary_point=right_coord,
                    sigma_y_m=round(sig_y, 1),
                    sigma_z_m=round(sig_z, 1),
                    lateral_width_km=total_width_km,
                    relative_concentration=0.0,  # normalized in next step
                )
            )

        # 6. Normalize relative concentrations to peak = 1.0
        peak_conc = max(raw_concentrations) if raw_concentrations else 1.0
        if peak_conc <= 0.0 or not math.isfinite(peak_conc):
            peak_conc = 1.0

        normalized_samples: list[DispersionSamplePoint] = []
        for pt, raw_c in zip(sample_points, raw_concentrations, strict=False):
            rel_c = round(max(0.0, min(1.0, raw_c / peak_conc)), 4)
            normalized_samples.append(
                pt.model_copy(update={"relative_concentration": rel_c})
            )

        # 7. Model confidence rating
        if data_quality == DataQuality.FALLBACK:
            confidence = "DEGRADED"
        elif wind.is_calm:
            confidence = "DEGRADED_CALM"
        elif data_quality == DataQuality.LIVE:
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"

        summary = DispersionSummary(
            model_name="Gaussian Atmospheric Dispersion (Briggs Parameterization)",
            is_engineering_approximation=True,
            stability_class=stability,
            stability_rationale=rationale,
            effective_release_height_m=round(eff_release_h, 1),
            source_strength_proxy=round(q_proxy, 4),
            max_hazard_distance_km=round(max_dist_km, 2),
            max_hazard_width_km=round(max_lateral_width_km, 2),
            plume_angle_deg=round(downwind_deg, 1),
            calm_stagnation_flag=wind.is_calm,
        )

        return AtmosphericDispersionResult(
            source_location=Coordinate(latitude=valid_lat, longitude=valid_lon),
            event_id=event_id,
            evaluated_at=datetime.now(timezone.utc),
            wind=wind,
            dispersion=summary,
            trajectory=normalized_samples,
            data_quality=data_quality,
            model_confidence=confidence,
        )
