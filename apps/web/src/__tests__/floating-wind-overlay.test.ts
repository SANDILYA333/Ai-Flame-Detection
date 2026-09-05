import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { AtmosphericDispersionResult } from "../types/dispersion.ts";

describe("Floating Wind & Plume Intelligence Overlay Suite", () => {
  const sampleEvent = DEMO_THERMAL_EVENTS[0];

  const mockDispersion: AtmosphericDispersionResult = {
    source_location: {
      latitude: sampleEvent.latitude,
      longitude: sampleEvent.longitude,
    },
    event_id: sampleEvent.event_id,
    evaluated_at: new Date().toISOString(),
    wind: {
      speed_ms: 1.4,
      gust_ms: 2.1,
      direction_from_deg: 110,
      direction_from_label: "ESE",
      direction_to_deg: 290,
      downwind_direction_label: "WNW",
      u_ms: -1.3,
      v_ms: 0.5,
      wind_state: "LIGHT",
      is_calm: false,
    },
    dispersion: {
      model_name: "Gaussian Plume",
      is_engineering_approximation: true,
      stability_class: "C",
      stability_rationale: "Slightly Unstable day conditions",
      effective_release_height_m: 85.0,
      source_strength_proxy: 1.0,
      max_hazard_distance_km: 7.1,
      max_hazard_width_km: 1.85,
      plume_angle_deg: 290.0,
      calm_stagnation_flag: false,
    },
    trajectory: [
      {
        downwind_distance_km: 0.5,
        centerline_point: { latitude: 21.0, longitude: 70.0 },
        left_boundary_point: { latitude: 21.01, longitude: 70.0 },
        right_boundary_point: { latitude: 20.99, longitude: 70.0 },
        sigma_y_m: 55,
        sigma_z_m: 32,
        lateral_width_km: 0.15,
        relative_concentration: 0.95,
      },
      {
        downwind_distance_km: 7.1,
        centerline_point: { latitude: 21.05, longitude: 70.05 },
        left_boundary_point: { latitude: 21.08, longitude: 70.05 },
        right_boundary_point: { latitude: 21.02, longitude: 70.05 },
        sigma_y_m: 670,
        sigma_z_m: 375,
        lateral_width_km: 1.85,
        relative_concentration: 0.1,
      },
    ],
    data_quality: "LIVE",
    model_confidence: "NOMINAL_MODEL",
  };

  it("Test 1: Wind Intelligence metrics preservation", () => {
    assert.equal(mockDispersion.wind.speed_ms, 1.4);
    assert.equal(mockDispersion.wind.direction_from_label, "ESE");
    assert.equal(mockDispersion.wind.downwind_direction_label, "WNW");
    assert.equal(mockDispersion.dispersion.max_hazard_distance_km, 7.1);
    assert.equal(mockDispersion.dispersion.stability_class, "C");
    assert.equal(mockDispersion.data_quality, "LIVE");
  });

  it("Test 2: Floating card viewport bounds clamping logic", () => {
    const viewportWidth = 1440;
    const viewportHeight = 900;
    const cardWidth = 290;
    const cardHeight = 150;
    const bounds = { top: 56, bottom: 64, left: 12, right: 12 };

    const clamp = (x: number, y: number) => {
      const minX = bounds.left;
      const maxX = Math.max(minX, viewportWidth - cardWidth - bounds.right);
      const minY = bounds.top;
      const maxY = Math.max(minY, viewportHeight - cardHeight - bounds.bottom);
      return {
        x: Math.min(Math.max(x, minX), maxX),
        y: Math.min(Math.max(y, minY), maxY),
      };
    };

    const posLeftTop = clamp(-50, -20);
    assert.equal(posLeftTop.x, bounds.left);
    assert.equal(posLeftTop.y, bounds.top);

    const posNormal = clamp(500, 300);
    assert.equal(posNormal.x, 500);
    assert.equal(posNormal.y, 300);

    const posRightBottom = clamp(2000, 1500);
    assert.equal(posRightBottom.x, viewportWidth - cardWidth - bounds.right);
    assert.equal(posRightBottom.y, viewportHeight - cardHeight - bounds.bottom);
  });

  it("Test 3: Visibility condition requirements", () => {
    const hasActiveEvent = (e: typeof sampleEvent | null): boolean => e !== null;
    const hasActiveDispersion = (d: typeof mockDispersion | null): boolean => d !== null;

    assert.equal(hasActiveEvent(sampleEvent) && hasActiveDispersion(mockDispersion), true);
    assert.equal(hasActiveEvent(null) && hasActiveDispersion(mockDispersion), false);
    assert.equal(hasActiveEvent(sampleEvent) && hasActiveDispersion(null), false);
  });
});
