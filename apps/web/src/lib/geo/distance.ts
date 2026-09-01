/**
 * Geodesic spatial calculation utilities based on the WGS-84 ellipsoid sphere approximation.
 */

const EARTH_RADIUS_METERS = 6371000; // Mean Earth radius in meters

/**
 * Calculates the great-circle geodesic distance between two points on Earth using the Haversine formula.
 * @param lat1 Latitude of point 1 in decimal degrees
 * @param lon1 Longitude of point 1 in decimal degrees
 * @param lat2 Latitude of point 2 in decimal degrees
 * @param lon2 Longitude of point 2 in decimal degrees
 * @returns Geodesic distance in meters
 */
export function calculateHaversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  if (
    typeof lat1 !== "number" ||
    typeof lon1 !== "number" ||
    typeof lat2 !== "number" ||
    typeof lon2 !== "number" ||
    isNaN(lat1) ||
    isNaN(lon1) ||
    isNaN(lat2) ||
    isNaN(lon2)
  ) {
    return 0;
  }

  const toRad = (deg: number) => (deg * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return Math.round(EARTH_RADIUS_METERS * c);
}

/**
 * Formats a metric distance into human-readable meters or kilometers.
 */
export function formatDistance(distanceMeters: number | null | undefined): string {
  if (distanceMeters === null || distanceMeters === undefined || isNaN(distanceMeters)) {
    return "N/A";
  }

  if (distanceMeters < 0) return "0 m";

  if (distanceMeters < 1000) {
    return `${Math.round(distanceMeters)} m`;
  }

  const km = distanceMeters / 1000;
  return `${km >= 10 ? km.toFixed(0) : km.toFixed(1)} km`;
}

/**
 * Evaluates operational industrial exposure tier based on geodesic proximity.
 */
export function calculateExposureLevel(
  distanceMeters: number | null | undefined
): "HIGH" | "MEDIUM" | "LOW" | "NONE" {
  if (distanceMeters === null || distanceMeters === undefined || isNaN(distanceMeters)) {
    return "NONE";
  }

  if (distanceMeters <= 500) {
    return "HIGH";
  }
  if (distanceMeters <= 2000) {
    return "MEDIUM";
  }
  return "LOW";
}
