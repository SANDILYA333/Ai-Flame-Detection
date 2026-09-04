import { test, describe } from "node:test";
import assert from "node:assert/strict";
import {
  computeCirclePolygon,
  isValidCoordinate,
  validateAndConvertDispersionToGeoJson,
} from "../lib/gis/dispersion-geojson.ts";
import type { AtmosphericDispersionResult } from "../types/dispersion.ts";

function createMockDispersion(
  isCalm = false,
  speedMs = 6.0,
  stability: "A" | "B" | "C" | "D" | "E" | "F" = "D"
): AtmosphericDispersionResult {
  return {
    source_location: { latitude: 22.38, longitude: 69.87 },
    event_id: "EVT-TEST-001",
    evaluated_at: "2026-09-04T10:00:00Z",
    wind: {
      speed_ms: speedMs,
      direction_from_deg: 225.0,
      direction_from_label: "SW",
      direction_to_deg: 45.0,
      downwind_direction_label: "NE",
      gust_ms: 8.5,
      u_ms: 4.24,
      v_ms: 4.24,
      is_calm: isCalm,
      wind_state: isCalm ? "CALM" : "MODERATE",
    },
    dispersion: {
      model_name: "Gaussian Atmospheric Dispersion (Briggs Parameterization)",
      is_engineering_approximation: true,
      stability_class: stability,
      stability_rationale: "Daytime moderate wind",
      effective_release_height_m: 25.0,
      source_strength_proxy: 7.071,
      max_hazard_distance_km: 8.5,
      max_hazard_width_km: 2.2,
      plume_angle_deg: 45.0,
      calm_stagnation_flag: isCalm,
    },
    trajectory: [
      {
        downwind_distance_km: 0.5,
        centerline_point: { latitude: 22.383, longitude: 69.873 },
        left_boundary_point: { latitude: 22.384, longitude: 69.872 },
        right_boundary_point: { latitude: 22.382, longitude: 69.874 },
        sigma_y_m: 40.0,
        sigma_z_m: 30.0,
        lateral_width_km: 0.17,
        relative_concentration: 0.95,
      },
      {
        downwind_distance_km: 2.0,
        centerline_point: { latitude: 22.392, longitude: 69.882 },
        left_boundary_point: { latitude: 22.395, longitude: 69.879 },
        right_boundary_point: { latitude: 22.389, longitude: 69.885 },
        sigma_y_m: 140.0,
        sigma_z_m: 80.0,
        lateral_width_km: 0.6,
        relative_concentration: 0.5,
      },
      {
        downwind_distance_km: 8.5,
        centerline_point: { latitude: 22.434, longitude: 69.924 },
        left_boundary_point: { latitude: 22.445, longitude: 69.913 },
        right_boundary_point: { latitude: 22.423, longitude: 69.935 },
        sigma_y_m: 520.0,
        sigma_z_m: 210.0,
        lateral_width_km: 2.2,
        relative_concentration: 0.08,
      },
    ],
    data_quality: "LIVE",
    model_confidence: isCalm ? "DEGRADED_CALM" : "HIGH",
  };
}

describe("Dispersion GeoJSON Transformation & Validation Suite", () => {
  test("isValidCoordinate accurately validates geographic range and finite values", () => {
    assert.equal(isValidCoordinate(22.38, 69.87), true);
    assert.equal(isValidCoordinate(-33.86, 151.2), true);
    assert.equal(isValidCoordinate(95.0, 70.0), false);
    assert.equal(isValidCoordinate(20.0, 195.0), false);
    assert.equal(isValidCoordinate(NaN, 70.0), false);
    assert.equal(isValidCoordinate(undefined, 70.0), false);
  });

  test("computeCirclePolygon generates closed polygon rings", () => {
    const ring = computeCirclePolygon(22.38, 69.87, 1.5, 36);
    assert.ok(ring.length > 30);
    // Closed ring: first point equals last point
    const first = ring[0];
    const last = ring[ring.length - 1];
    assert.equal(first[0], last[0]);
    assert.equal(first[1], last[1]);
  });

  test("validateAndConvertDispersionToGeoJson builds complete FeatureCollection", () => {
    const mock = createMockDispersion();
    const geojson = validateAndConvertDispersionToGeoJson(mock);

    assert.equal(geojson.type, "FeatureCollection");
    assert.equal(geojson.features.length, 4);

    const plume = geojson.features.find((f) => f.id === "selected-incident-plume");
    const centerline = geojson.features.find((f) => f.id === "selected-incident-centerline");
    const isolation = geojson.features.find((f) => f.id === "selected-incident-isolation-zone");
    const evac = geojson.features.find((f) => f.id === "selected-incident-evacuation-corridor");

    assert.ok(plume, "Plume feature must exist");
    assert.ok(centerline, "Centerline feature must exist");
    assert.ok(isolation, "Isolation feature must exist");
    assert.ok(evac, "Evacuation feature must exist");

    assert.equal(plume.geometry.type, "Polygon");
    assert.equal(centerline.geometry.type, "LineString");
    assert.equal(isolation.geometry.type, "Polygon");
    assert.equal(evac.geometry.type, "Polygon");

    // Verify plume polygon is closed
    const coords = plume.geometry.coordinates[0];
    assert.deepEqual(coords[0], coords[coords.length - 1]);
    assert.equal(plume.properties.bearing_deg, 45.0);
    assert.equal(plume.properties.max_distance_km, 8.5);
  });

  test("validateAndConvertDispersionToGeoJson handles calm wind stagnation", () => {
    const calmMock = createMockDispersion(true, 0.2, "F");
    const geojson = validateAndConvertDispersionToGeoJson(calmMock);

    const plume = geojson.features.find((f) => f.id === "selected-incident-plume");
    assert.ok(plume);
    assert.equal(plume.properties.is_calm, true);
    assert.equal(plume.properties.model_confidence, "DEGRADED_CALM");
  });

  test("validateAndConvertDispersionToGeoJson handles null/empty/invalid input gracefully", () => {
    const nullRes = validateAndConvertDispersionToGeoJson(null);
    assert.equal(nullRes.type, "FeatureCollection");
    assert.equal(nullRes.features.length, 0);

    const emptyTrajectory = createMockDispersion();
    emptyTrajectory.trajectory = [];
    const emptyRes = validateAndConvertDispersionToGeoJson(emptyTrajectory);
    assert.equal(emptyRes.features.length, 0);

    const invalidCoord = createMockDispersion();
    invalidCoord.source_location.latitude = NaN;
    const invalidRes = validateAndConvertDispersionToGeoJson(invalidCoord);
    assert.equal(invalidRes.features.length, 0);
  });
});
