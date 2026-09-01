/**
 * Technical geospatial coordinate formatting
 */

export function formatCoordinate(lat: number, lon: number, precision: number = 4): string {
  const safeLat = typeof lat === "number" && !isNaN(lat) && isFinite(lat) ? lat : 0;
  const safeLon = typeof lon === "number" && !isNaN(lon) && isFinite(lon) ? lon : 0;
  const latDir = safeLat >= 0 ? "N" : "S";
  const lonDir = safeLon >= 0 ? "E" : "W";
  return `${Math.abs(safeLat).toFixed(precision)}° ${latDir}, ${Math.abs(safeLon).toFixed(precision)}° ${lonDir}`;
}

export function formatCompactCoordinate(lat: number, lon: number): string {
  const safeLat = typeof lat === "number" && !isNaN(lat) && isFinite(lat) ? lat : 0;
  const safeLon = typeof lon === "number" && !isNaN(lon) && isFinite(lon) ? lon : 0;
  return `${safeLat.toFixed(2)}°, ${safeLon.toFixed(2)}°`;
}
