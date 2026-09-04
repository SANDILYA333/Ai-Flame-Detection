/**
 * GeoJSON conversion and validation utilities for Atmospheric Dispersion & Downwind Hazard Intelligence (Phase 4).
 */

import type { AtmosphericDispersionResult, PlumeHazardGeoJson } from "@/types/dispersion";

/**
 * Generate a 36-point circle polygon coordinate array around a center coordinate.
 */
export function computeCirclePolygon(
  lat: number,
  lon: number,
  radiusKm: number,
  steps = 36
): [number, number][] {
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(radiusKm) || radiusKm <= 0) {
    return [];
  }

  const R = 6371.0; // Earth's mean radius in km
  const pts: [number, number][] = [];
  const radLat = (lat * Math.PI) / 180;
  const radLon = (lon * Math.PI) / 180;
  const angDist = radiusKm / R;

  for (let i = 0; i <= steps; i++) {
    const bearing = (i * (360 / steps) * Math.PI) / 180;
    const lat2 = Math.asin(
      Math.sin(radLat) * Math.cos(angDist) +
        Math.cos(radLat) * Math.sin(angDist) * Math.cos(bearing)
    );
    const lon2 =
      radLon +
      Math.atan2(
        Math.sin(bearing) * Math.sin(angDist) * Math.cos(radLat),
        Math.cos(angDist) - Math.sin(radLat) * Math.sin(lat2)
      );

    const degLon = Number(((lon2 * 180) / Math.PI).toFixed(6));
    const degLat = Number(((lat2 * 180) / Math.PI).toFixed(6));
    pts.push([degLon, degLat]);
  }

  return pts;
}

/**
 * Validates coordinates and ensures finite float values.
 */
export function isValidCoordinate(lat: unknown, lon: unknown): boolean {
  if (typeof lat !== "number" || typeof lon !== "number") return false;
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  return lat >= -90.0 && lat <= 90.0 && lon >= -180.0 && lon <= 180.0;
}

/**
 * Validates and transforms canonical backend AtmosphericDispersionResult into MapLibre-ready GeoJSON features.
 *
 * Guaranteed error-safe: If input data is malformed or empty, gracefully returns an empty FeatureCollection
 * with diagnostic logging rather than crashing the map.
 */
export function validateAndConvertDispersionToGeoJson(
  dispersion: AtmosphericDispersionResult | null | undefined
): PlumeHazardGeoJson {
  const emptyResult: PlumeHazardGeoJson = {
    type: "FeatureCollection",
    features: [],
  };

  if (!dispersion) return emptyResult;

  try {
    const { source_location, trajectory, dispersion: summary, wind, data_quality, model_confidence } = dispersion;

    if (!source_location || !isValidCoordinate(source_location.latitude, source_location.longitude)) {
      console.warn("[WIND-GIS] Invalid dispersion source coordinate:", source_location);
      return emptyResult;
    }

    const srcLat = source_location.latitude;
    const srcLon = source_location.longitude;
    const srcCoord: [number, number] = [srcLon, srcLat];

    if (!Array.isArray(trajectory) || trajectory.length === 0) {
      console.warn("[WIND-GIS] Dispersion trajectory is empty");
      return emptyResult;
    }

    // 1. Validate trajectory sampling points
    const validPoints = trajectory.filter(
      (pt) =>
        pt &&
        pt.centerline_point &&
        isValidCoordinate(pt.centerline_point.latitude, pt.centerline_point.longitude) &&
        pt.left_boundary_point &&
        isValidCoordinate(pt.left_boundary_point.latitude, pt.left_boundary_point.longitude) &&
        pt.right_boundary_point &&
        isValidCoordinate(pt.right_boundary_point.latitude, pt.right_boundary_point.longitude)
    );

    if (validPoints.length === 0) {
      console.warn("[WIND-GIS] No valid trajectory points found in dispersion model");
      return emptyResult;
    }

    // 2. Build Gaussian Plume Hazard Polygon
    // Path: Source -> Left Boundaries -> Terminal End Cap -> Right Boundaries (reverse) -> Close to Source
    const plumePolygonCoords: [number, number][] = [srcCoord];

    // Left lateral boundary going downwind
    for (const pt of validPoints) {
      plumePolygonCoords.push([pt.left_boundary_point.longitude, pt.left_boundary_point.latitude]);
    }

    // Terminal crosswind arc / centerline cap
    const terminal = validPoints[validPoints.length - 1];
    plumePolygonCoords.push([terminal.centerline_point.longitude, terminal.centerline_point.latitude]);

    // Right lateral boundary returning upwind
    for (let i = validPoints.length - 1; i >= 0; i--) {
      const pt = validPoints[i];
      plumePolygonCoords.push([pt.right_boundary_point.longitude, pt.right_boundary_point.latitude]);
    }

    // Explicit polygon ring closure
    plumePolygonCoords.push(srcCoord);

    const plumeFeature = {
      type: "Feature" as const,
      id: "selected-incident-plume",
      geometry: {
        type: "Polygon" as const,
        coordinates: [plumePolygonCoords],
      },
      properties: {
        label: "MODELLED DOWNWIND HAZARD CORRIDOR",
        hazard_level: "DISPERSION_PLUME",
        max_distance_km: summary?.max_hazard_distance_km ?? 0,
        max_width_km: summary?.max_hazard_width_km ?? 0,
        bearing_deg: summary?.plume_angle_deg ?? wind?.direction_to_deg ?? 0,
        stability_class: summary?.stability_class ?? "D",
        is_calm: summary?.calm_stagnation_flag ?? wind?.is_calm ?? false,
        data_quality: data_quality,
        model_confidence: model_confidence,
      },
    };

    // 3. Build Downwind Centerline Trajectory LineString
    const centerlineCoords: [number, number][] = [srcCoord];
    for (const pt of validPoints) {
      centerlineCoords.push([pt.centerline_point.longitude, pt.centerline_point.latitude]);
    }

    const centerlineFeature = {
      type: "Feature" as const,
      id: "selected-incident-centerline",
      geometry: {
        type: "LineString" as const,
        coordinates: centerlineCoords,
      },
      properties: {
        label: "DOWNWIND DISPERSION CENTERLINE",
        hazard_level: "CENTERLINE",
        bearing_deg: summary?.plume_angle_deg ?? wind?.direction_to_deg ?? 0,
        wind_speed_ms: wind?.speed_ms ?? 0,
        direction_from_label: wind?.direction_from_label ?? "VAR",
        downwind_direction_label: wind?.downwind_direction_label ?? "VAR",
      },
    };

    // 4. Build Immediate Isolation Zone Circle (200m standard)
    const isolationRadiusKm = 0.2; // 200m
    const isolationCoords = computeCirclePolygon(srcLat, srcLon, isolationRadiusKm);

    const isolationFeature = {
      type: "Feature" as const,
      id: "selected-incident-isolation-zone",
      geometry: {
        type: "Polygon" as const,
        coordinates: [isolationCoords],
      },
      properties: {
        label: "INITIAL ISOLATION ZONE (200m)",
        hazard_level: "ISOLATION_ZONE",
        radius_m: 200,
      },
    };

    // 5. Build Evacuation Zone Circle (Modeled Initial Protective Distance)
    const evacRadiusKm = Math.min(
      3.5,
      Math.max(0.5, (summary?.max_hazard_distance_km ?? 2.0) * 0.4)
    );
    const evacCoords = computeCirclePolygon(srcLat, srcLon, evacRadiusKm);

    const evacFeature = {
      type: "Feature" as const,
      id: "selected-incident-evacuation-corridor",
      geometry: {
        type: "Polygon" as const,
        coordinates: [evacCoords],
      },
      properties: {
        label: "PROTECTIVE EVACUATION BUFFER",
        hazard_level: "EVACUATION_ZONE",
        radius_km: evacRadiusKm,
      },
    };

    return {
      type: "FeatureCollection",
      features: [plumeFeature, centerlineFeature, isolationFeature, evacFeature],
    };
  } catch (err) {
    console.error("[WIND-GIS] Failed to construct dispersion GeoJSON:", err);
    return emptyResult;
  }
}
