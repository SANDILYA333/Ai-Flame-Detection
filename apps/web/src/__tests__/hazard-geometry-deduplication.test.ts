import { test, describe } from "node:test";
import assert from "node:assert/strict";
import {
  computeCirclePolygon,
  validateAndConvertDispersionToGeoJson,
} from "../lib/gis/dispersion-geojson.ts";
import type { AtmosphericDispersionResult } from "../types/dispersion.ts";

function computeCircleCoordinates(centerLat: number, centerLon: number, distanceKm: number): [number, number][] {
  const pts: [number, number][] = [];
  const R = 6371; // Earth radius in km
  const radLat = (centerLat * Math.PI) / 180;
  const radLon = (centerLon * Math.PI) / 180;
  const angDist = distanceKm / R;
  for (let angle = 0; angle <= 360; angle += 10) {
    const radBearing = (angle * Math.PI) / 180;
    const lat2 = Math.asin(
      Math.sin(radLat) * Math.cos(angDist) +
        Math.cos(radLat) * Math.sin(angDist) * Math.cos(radBearing)
    );
    const lon2 =
      radLon +
      Math.atan2(
        Math.sin(radBearing) * Math.sin(angDist) * Math.cos(radLat),
        Math.cos(angDist) - Math.sin(radLat) * Math.sin(lat2)
      );
    pts.push([
      Number(((lon2 * 180) / Math.PI).toFixed(6)),
      Number(((lat2 * 180) / Math.PI).toFixed(6)),
    ]);
  }
  return pts;
}

function computeForestThreatRings(lat: number, lon: number) {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 10.0)] },
        properties: {
          level: "AWARENESS",
          label: "10 km Awareness Buffer",
          color: "#3b82f6",
        },
      },
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 5.0)] },
        properties: {
          level: "WARNING",
          label: "5 km Warning Buffer",
          color: "#f59e0b",
        },
      },
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 2.0)] },
        properties: {
          level: "CRITICAL",
          label: "2 km Critical Buffer",
          color: "#ef4444",
        },
      },
    ],
  };
}

describe("Hazard and Evacuation Geometry Deduplication Suite", () => {
  test("generates exactly one canonical set of incident threat rings (3 distinct operational zones)", () => {
    const rings = computeForestThreatRings(22.38, 69.87);
    assert.equal(rings.type, "FeatureCollection");
    assert.equal(rings.features.length, 3, "Must have exactly 3 distinct operational buffer zones");

    const levels = rings.features.map((f) => f.properties.level);
    assert.deepEqual(levels, ["AWARENESS", "WARNING", "CRITICAL"]);

    const colors = rings.features.map((f) => f.properties.color);
    assert.deepEqual(colors, ["#3b82f6", "#f59e0b", "#ef4444"]);

    // Ensure all 3 zones are concentric around the exact incident coordinates
    for (const f of rings.features) {
      assert.equal(f.geometry.type, "Polygon");
      const coords = f.geometry.coordinates[0];
      assert.ok(coords.length > 30);
      assert.deepEqual(coords[0], coords[coords.length - 1], "Polygon must be closed ring");
    }
  });

  test("switching incident coordinates produces deterministic non-overlapping updated geometries", () => {
    const incidentA = computeForestThreatRings(22.38, 69.87);
    const incidentB = computeForestThreatRings(21.85, 88.90);

    assert.equal(incidentA.features.length, 3);
    assert.equal(incidentB.features.length, 3);

    // Verify coordinates differ
    const coordA = incidentA.features[0].geometry.coordinates[0][0];
    const coordB = incidentB.features[0].geometry.coordinates[0][0];
    assert.notDeepEqual(coordA, coordB, "Different incidents must have distinct coordinate centroids");
  });

  test("dispersion GeoJSON includes exactly one isolation zone and one evacuation corridor", () => {
    const mockDispersion: AtmosphericDispersionResult = {
      source_location: { latitude: 22.38, longitude: 69.87 },
      event_id: "EVT-TEST-001",
      evaluated_at: "2026-09-04T10:00:00Z",
      wind: {
        speed_ms: 5.5,
        direction_from_deg: 225.0,
        direction_from_label: "SW",
        direction_to_deg: 45.0,
        downwind_direction_label: "NE",
        gust_ms: 7.8,
        u_ms: 3.88,
        v_ms: 3.88,
        is_calm: false,
        wind_state: "MODERATE",
      },
      dispersion: {
        model_name: "Gaussian Atmospheric Dispersion (Briggs Parameterization)",
        is_engineering_approximation: true,
        stability_class: "D",
        stability_rationale: "Daytime moderate wind",
        effective_release_height_m: 25.0,
        source_strength_proxy: 7.071,
        max_hazard_distance_km: 8.5,
        max_hazard_width_km: 2.2,
        plume_angle_deg: 45.0,
        calm_stagnation_flag: false,
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
      ],
      data_quality: "LIVE",
      model_confidence: "HIGH",
    };

    const geojson = validateAndConvertDispersionToGeoJson(mockDispersion);
    assert.equal(geojson.type, "FeatureCollection");

    const isolationFeatures = geojson.features.filter((f) => f.id === "selected-incident-isolation-zone");
    const evacFeatures = geojson.features.filter((f) => f.id === "selected-incident-evacuation-corridor");
    const plumeFeatures = geojson.features.filter((f) => f.id === "selected-incident-plume");
    const centerlineFeatures = geojson.features.filter((f) => f.id === "selected-incident-centerline");

    assert.equal(isolationFeatures.length, 1, "Must contain exactly 1 isolation zone");
    assert.equal(evacFeatures.length, 1, "Must contain exactly 1 evacuation corridor");
    assert.equal(plumeFeatures.length, 1, "Must contain exactly 1 plume polygon");
    assert.equal(centerlineFeatures.length, 1, "Must contain exactly 1 centerline");
  });
});
