/**
 * 3D Globe Spherical Geometry Normalization Utilities
 *
 * In standard planar GeoJSON (RFC 7946), polygon exterior rings are oriented
 * counter-clockwise (positive planar area) and holes are clockwise.
 *
 * However, spherical polygon geometry engines (such as Three-Globe,
 * three-conic-polygon-geometry, and d3-geo) interpret CCW exterior rings
 * as enclosing the complement of the sphere (the entire Earth minus the feature,
 * area ~ 4π steradians), which causes whole-globe mesh rendering bugs.
 *
 * This module normalizes polygon geometries specifically for 3D spherical globe
 * rendering while preserving the original datasets for 2D map views.
 */

export interface GeoJsonGeometry {
  type: string;
  coordinates: any;
}

/**
 * Calculates the signed planar Shoelace area of a 2D coordinate ring.
 * - Positive (> 0): Counter-Clockwise (CCW)
 * - Negative (< 0): Clockwise (CW)
 */
export function getRingSignedPlanarArea(ring: number[][]): number {
  if (!Array.isArray(ring) || ring.length < 3) return 0;
  let sum = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const p1 = ring[i];
    const p2 = ring[i + 1];
    if (Array.isArray(p1) && Array.isArray(p2) && Number.isFinite(p1[0]) && Number.isFinite(p2[0])) {
      sum += p1[0] * p2[1] - p2[0] * p1[1];
    }
  }
  return sum / 2;
}

/**
 * Validates whether a geometry object is a valid, renderable Polygon or MultiPolygon.
 */
export function isGlobePolygonValid(geometry: any): boolean {
  if (!geometry || typeof geometry !== "object") return false;
  if (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon") return false;
  if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length === 0) return false;
  return true;
}

/**
 * Normalizes a single ring for 3D spherical rendering:
 * - Closes unclosed rings.
 * - For outer rings (isOuterRing = true), ensures Clockwise winding (area < 0) so spherical area < 2π.
 * - For hole rings (isOuterRing = false), ensures Counter-Clockwise winding (area > 0).
 */
export function normalizeSphericalRing(ring: number[][], isOuterRing: boolean): number[][] {
  if (!Array.isArray(ring) || ring.length < 3) return ring;

  // Filter out non-finite coordinates
  const validCoords = ring.filter(
    (pt) => Array.isArray(pt) && Number.isFinite(pt[0]) && Number.isFinite(pt[1])
  );
  if (validCoords.length < 3) return ring;

  // Ensure ring closure
  const cleanRing = [...validCoords];
  const first = cleanRing[0];
  const last = cleanRing[cleanRing.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    cleanRing.push([first[0], first[1]]);
  }

  const area = getRingSignedPlanarArea(cleanRing);

  // In 3D spherical geometry:
  // Outer ring MUST be Clockwise (area < 0)
  // Hole ring MUST be Counter-Clockwise (area > 0)
  if (isOuterRing) {
    return area > 0 ? cleanRing.reverse() : cleanRing;
  } else {
    return area < 0 ? cleanRing.reverse() : cleanRing;
  }
}

/**
 * Normalizes a GeoJSON Polygon or MultiPolygon geometry for 3D Globe rendering.
 */
export function normalizeGlobePolygonGeometry<T extends GeoJsonGeometry>(geometry: T): T {
  if (!isGlobePolygonValid(geometry)) {
    return geometry;
  }

  if (geometry.type === "Polygon") {
    const coords = geometry.coordinates as number[][][];
    const normalized = coords.map((ring, idx) =>
      normalizeSphericalRing(ring, idx === 0)
    );
    return {
      ...geometry,
      coordinates: normalized,
    };
  }

  if (geometry.type === "MultiPolygon") {
    const coords = geometry.coordinates as number[][][][];
    const normalized = coords.map((polyRings) =>
      polyRings.map((ring, idx) => normalizeSphericalRing(ring, idx === 0))
    );
    return {
      ...geometry,
      coordinates: normalized,
    };
  }

  return geometry;
}
