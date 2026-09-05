import { describe, it } from "node:test";
import assert from "node:assert/strict";
// @ts-ignore
import * as d3Geo from "d3-geo";
import { DEMO_FORESTS_GEOJSON } from "../features/forests/mock/demo-forests.ts";
import {
  normalizeGlobePolygonGeometry,
  normalizeSphericalRing,
  getRingSignedPlanarArea,
  isGlobePolygonValid,
} from "../lib/map/globe-geometry.ts";

describe("3D Globe Forest Reserves Geometry Normalization Suite", () => {
  it("Test 1: Normalizes CCW polygon exterior ring to clockwise (spherical area < 2π)", () => {
    // Standard RFC 7946 Counter-Clockwise polygon
    const ccwPolygon = {
      type: "Polygon" as const,
      coordinates: [
        [
          [70.50, 21.05],
          [70.90, 21.05],
          [70.95, 21.30],
          [70.55, 21.35],
          [70.50, 21.05],
        ],
      ],
    };

    // Raw CCW polygon in d3-geo encloses ~ 4π steradians (the entire earth)
    const rawSphericalArea = d3Geo.geoArea(ccwPolygon);
    const rawBounds = d3Geo.geoBounds(ccwPolygon);
    assert.ok(rawSphericalArea > 2 * Math.PI, "Raw CCW polygon unexpectedly had small area");
    assert.deepEqual(rawBounds, [[-180, -90], [180, 90]], "Raw CCW polygon did not span whole earth in d3-geo");

    // Normalized polygon for 3D globe
    const normalized = normalizeGlobePolygonGeometry(ccwPolygon);
    const normSphericalArea = d3Geo.geoArea(normalized);
    const normBounds = d3Geo.geoBounds(normalized);

    assert.ok(normSphericalArea < 2 * Math.PI, "Normalized polygon spherical area must be < 2π");
    assert.ok(normSphericalArea < 0.001, "Normalized forest polygon should have tiny fractional area");
    assert.equal(normBounds[0][0], 70.5);
    assert.equal(normBounds[0][1], 21.05);
    assert.equal(normBounds[1][0], 70.95);
    assert.equal(normBounds[1][1], 21.35);
  });

  it("Test 2: All DEMO_FORESTS_GEOJSON features have bounded local coordinates on 3D globe", () => {
    assert.ok(DEMO_FORESTS_GEOJSON.features.length >= 6);

    for (const feature of DEMO_FORESTS_GEOJSON.features) {
      assert.ok(isGlobePolygonValid(feature.geometry), `Feature ${feature.properties.name} has invalid geometry`);

      const normalizedGeom = normalizeGlobePolygonGeometry(feature.geometry);
      const sphericalArea = d3Geo.geoArea(normalizedGeom);
      const bounds = d3Geo.geoBounds(normalizedGeom);

      // Area must be bounded (< 0.01 steradians for regional reserves, never ~ 12.566)
      assert.ok(
        sphericalArea < 0.05,
        `Feature ${feature.properties.name} exceeded maximum expected spherical area: ${sphericalArea}`
      );

      // Bounding box must not cover the entire planet
      assert.notDeepEqual(
        bounds,
        [[-180, -90], [180, 90]],
        `Feature ${feature.properties.name} spans the entire globe!`
      );

      // Bounds must be within valid geographic range
      assert.ok(bounds[0][0] >= -180 && bounds[0][0] <= 180);
      assert.ok(bounds[1][0] >= -180 && bounds[1][0] <= 180);
      assert.ok(bounds[0][1] >= -90 && bounds[0][1] <= 90);
      assert.ok(bounds[1][1] >= -90 && bounds[1][1] <= 90);
    }
  });

  it("Test 3: Preserves and normalizes MultiPolygon geometries with multiple polygons", () => {
    const multiPolygon = {
      type: "MultiPolygon" as const,
      coordinates: [
        [
          [
            [70.50, 21.05],
            [70.90, 21.05],
            [70.95, 21.30],
            [70.55, 21.35],
            [70.50, 21.05],
          ],
        ],
        [
          [
            [88.40, 21.60],
            [89.10, 21.60],
            [89.15, 22.00],
            [88.45, 22.05],
            [88.40, 21.60],
          ],
        ],
      ],
    };

    const normalized = normalizeGlobePolygonGeometry(multiPolygon);
    assert.equal(normalized.type, "MultiPolygon");
    assert.equal(normalized.coordinates.length, 2);

    const sphericalArea = d3Geo.geoArea(normalized);
    assert.ok(sphericalArea < 2 * Math.PI, "MultiPolygon area must be < 2π");
    assert.ok(sphericalArea < 0.001, "MultiPolygon should have small local area");
  });

  it("Test 4: Handles polygon holes with opposing winding order", () => {
    const polygonWithHole = {
      type: "Polygon" as const,
      coordinates: [
        // Outer ring (CCW in planar GeoJSON)
        [
          [10.0, 10.0],
          [20.0, 10.0],
          [20.0, 20.0],
          [10.0, 20.0],
          [10.0, 10.0],
        ],
        // Inner hole ring (CW in planar GeoJSON)
        [
          [13.0, 13.0],
          [13.0, 17.0],
          [17.0, 17.0],
          [17.0, 13.0],
          [13.0, 13.0],
        ],
      ],
    };

    const normalized = normalizeGlobePolygonGeometry(polygonWithHole);
    assert.equal(normalized.coordinates.length, 2);

    // Outer ring must be CW (negative planar area)
    const outerPlanarArea = getRingSignedPlanarArea(normalized.coordinates[0]);
    assert.ok(outerPlanarArea < 0, "Normalized outer ring must be clockwise");

    // Hole ring must be CCW (positive planar area)
    const holePlanarArea = getRingSignedPlanarArea(normalized.coordinates[1]);
    assert.ok(holePlanarArea > 0, "Normalized hole ring must be counter-clockwise");
  });

  it("Test 5: Resilience against malformed, unclosed, and non-polygon inputs", () => {
    // Unclosed ring
    const unclosed = normalizeSphericalRing(
      [
        [70.50, 21.05],
        [70.90, 21.05],
        [70.95, 21.30],
        [70.55, 21.35],
      ],
      true
    );
    assert.deepEqual(unclosed[0], unclosed[unclosed.length - 1], "Unclosed ring was not closed");

    // Non-polygon inputs
    assert.equal(isGlobePolygonValid(null), false);
    assert.equal(isGlobePolygonValid(undefined), false);
    assert.equal(isGlobePolygonValid({ type: "Point", coordinates: [70, 21] }), false);
    assert.equal(isGlobePolygonValid({ type: "Polygon", coordinates: [] }), false);

    // Pass-through for invalid
    const invalidObj = { type: "Point", coordinates: [70, 21] };
    assert.deepEqual(normalizeGlobePolygonGeometry(invalidObj as any), invalidObj);
  });

  it("Test 6: Layer toggle state yields empty array when inactive and populated array when active", () => {
    const isForestLayerActive = false;
    const features = DEMO_FORESTS_GEOJSON.features;

    const computeActive = (active: boolean) => {
      if (!active || !features?.length) return [];
      return features
        .filter((f) => f && isGlobePolygonValid(f.geometry))
        .map((f) => ({
          ...f,
          geometry: normalizeGlobePolygonGeometry(f.geometry),
        }));
    };

    const inactiveResult = computeActive(false);
    assert.equal(inactiveResult.length, 0);

    const activeResult = computeActive(true);
    assert.equal(activeResult.length, DEMO_FORESTS_GEOJSON.features.length);
  });
});
