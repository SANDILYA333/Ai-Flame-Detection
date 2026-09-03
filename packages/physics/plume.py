"""Gaussian plume dispersion hazard and evacuation zone modeling (PHYS-002)."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PlumeHazardModel:
    """Modeled downwind dispersion plume and emergency evacuation buffer."""

    origin_latitude: float
    origin_longitude: float
    wind_speed_ms: float
    wind_direction_deg: float
    downwind_azimuth_deg: float
    plume_length_km: float
    plume_width_km: float
    evacuation_radius_km: float
    plume_polygon_geojson: dict
    evacuation_circle_geojson: dict
    stability_class: str
    hazard_label: str

    def to_dict(self) -> dict:
        return {
            "origin_latitude": self.origin_latitude,
            "origin_longitude": self.origin_longitude,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_direction_deg": self.wind_direction_deg,
            "downwind_azimuth_deg": self.downwind_azimuth_deg,
            "plume_length_km": round(self.plume_length_km, 2),
            "plume_width_km": round(self.plume_width_km, 2),
            "evacuation_radius_km": round(self.evacuation_radius_km, 2),
            "plume_polygon_geojson": self.plume_polygon_geojson,
            "evacuation_circle_geojson": self.evacuation_circle_geojson,
            "stability_class": self.stability_class,
            "hazard_label": self.hazard_label,
        }


class GaussianPlumeEngine:
    """Atmospheric dispersion engine generating downwind hazard zones."""

    EARTH_RADIUS_KM: float = 6371.0

    @classmethod
    def _offset_point(
        cls, lat: float, lon: float, distance_km: float, bearing_deg: float
    ) -> list[float]:
        """Project coordinate by distance and bearing using spherical geodesics."""
        rad_lat = math.radians(lat)
        rad_lon = math.radians(lon)
        rad_bearing = math.radians(bearing_deg)
        ang_dist = distance_km / cls.EARTH_RADIUS_KM

        lat2 = math.asin(
            math.sin(rad_lat) * math.cos(ang_dist)
            + math.cos(rad_lat) * math.sin(ang_dist) * math.cos(rad_bearing)
        )
        lon2 = rad_lon + math.atan2(
            math.sin(rad_bearing) * math.sin(ang_dist) * math.cos(rad_lat),
            math.cos(ang_dist) - math.sin(rad_lat) * math.sin(lat2),
        )

        return [round(math.degrees(lon2), 6), round(math.degrees(lat2), 6)]

    @classmethod
    def compute_plume(
        cls,
        latitude: float,
        longitude: float,
        frp_mw: float,
        wind_speed_ms: float = 3.5,
        wind_direction_deg: float = 240.0,
    ) -> PlumeHazardModel:
        """Derive downwind dispersion polygon and evacuation boundary."""
        # Downwind azimuth = wind origin direction + 180 deg
        downwind_deg = (wind_direction_deg + 180.0) % 360.0

        # Physical scaling: Plume length scales with FRP and inversely with wind speed
        eff_frp = max(5.0, frp_mw)
        eff_wind = max(1.0, wind_speed_ms)
        plume_len_km = min(18.0, max(1.5, (math.sqrt(eff_frp) * 1.1) / eff_wind))
        plume_width_km = min(4.5, max(0.4, plume_len_km * 0.35))
        evac_radius_km = min(3.5, max(0.4, 0.25 * (eff_frp**0.35)))

        # Construct Plume Boundary Polygon (Teardrop / Cone expanding downwind)
        pts: list[list[float]] = []
        origin_coord = [round(longitude, 6), round(latitude, 6)]
        pts.append(origin_coord)

        # Left spreading edge
        half_angle = 18.0  # degrees half-angle expansion
        steps = 6
        for i in range(1, steps + 1):
            fraction = i / steps
            d_km = fraction * plume_len_km
            bearing = (downwind_deg - half_angle * (1.0 - 0.3 * fraction)) % 360.0
            pts.append(cls._offset_point(latitude, longitude, d_km, bearing))

        # Downwind apex arc
        for arc_angle in range(-12, 13, 6):
            bearing = (downwind_deg + arc_angle) % 360.0
            pts.append(cls._offset_point(latitude, longitude, plume_len_km, bearing))

        # Right spreading edge (in reverse back to origin)
        for i in range(steps, 0, -1):
            fraction = i / steps
            d_km = fraction * plume_len_km
            bearing = (downwind_deg + half_angle * (1.0 - 0.3 * fraction)) % 360.0
            pts.append(cls._offset_point(latitude, longitude, d_km, bearing))

        pts.append(origin_coord)  # Close ring

        plume_geojson = {
            "type": "Feature",
            "properties": {
                "type": "PLUME_HAZARD_POLYGON",
                "label": "MODELLED HAZARD / DISPERSION ESTIMATE",
                "frp_mw": frp_mw,
                "wind_speed_ms": wind_speed_ms,
                "downwind_azimuth_deg": downwind_deg,
                "plume_length_km": round(plume_len_km, 2),
                "is_modelled": True,
            },
            "geometry": {"type": "Polygon", "coordinates": [pts]},
        }

        # Construct Circular Evacuation Boundary
        circle_pts: list[list[float]] = []
        for angle in range(0, 361, 10):
            circle_pts.append(
                cls._offset_point(
                    latitude, longitude, evac_radius_km, float(angle)
                )
            )

        evac_geojson = {
            "type": "Feature",
            "properties": {
                "type": "EVACUATION_SAFETY_ZONE",
                "label": "ERG INITIAL ISOLATION BOUNDARY",
                "radius_km": round(evac_radius_km, 2),
                "is_modelled": True,
            },
            "geometry": {"type": "Polygon", "coordinates": [circle_pts]},
        }

        return PlumeHazardModel(
            origin_latitude=latitude,
            origin_longitude=longitude,
            wind_speed_ms=wind_speed_ms,
            wind_direction_deg=wind_direction_deg,
            downwind_azimuth_deg=downwind_deg,
            plume_length_km=plume_len_km,
            plume_width_km=plume_width_km,
            evacuation_radius_km=evac_radius_km,
            plume_polygon_geojson=plume_geojson,
            evacuation_circle_geojson=evac_geojson,
            stability_class="Pasquill Class D (Neutral)",
            hazard_label="MODELLED HAZARD / DISPERSION ESTIMATE",
        )
