import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { backendEventToThermalEvent } from "../types/event.ts";
import type { BackendEventItem } from "../types/event.ts";

describe("Event Rendering & Adapter Suite", () => {
  it("converts industrial backend event item to UI ThermalEvent correctly", () => {
    const backendItem: BackendEventItem = {
      event_id: "evt_c05e4698d63bbdf61c17b853",
      started_at: "2026-08-01T08:30:00Z",
      ended_at: "2026-08-01T08:30:00Z",
      duration_seconds: 0.0,
      centroid_latitude: 22.4506,
      centroid_longitude: 70.0516,
      detection_count: 2,
      mean_frp_mw: 35.3,
      max_frp_mw: 42.1,
      classification_state: "industrial",
      persistence_state: "transient",
    };

    const thermal = backendEventToThermalEvent(backendItem);

    assert.equal(thermal.event_id, "evt_c05e4698d63bbdf61c17b853");
    assert.equal(thermal.latitude, 22.4506);
    assert.equal(thermal.longitude, 70.0516);
    assert.equal(thermal.classification, "INDUSTRIAL");
    assert.equal(thermal.frp_mw, 42.1);
    assert.equal(thermal.detection_count, 2);
    assert.equal(thermal.start_time, "2026-08-01T08:30:00Z");
    assert.equal(thermal.uncertainty_state, "CONFIDENT");
  });

  it("handles unknown and insufficient_history states cleanly", () => {
    const backendItem: BackendEventItem = {
      event_id: "evt_36d53318a46480f2caa39be1",
      started_at: "2026-08-03T20:00:00Z",
      ended_at: "2026-08-03T20:00:00Z",
      duration_seconds: 0.0,
      centroid_latitude: 22.47,
      centroid_longitude: 70.075,
      detection_count: 1,
      mean_frp_mw: 24.7,
      max_frp_mw: 24.7,
      classification_state: "unknown",
      persistence_state: "insufficient_history",
    };

    const thermal = backendEventToThermalEvent(backendItem);

    assert.equal(thermal.event_id, "evt_36d53318a46480f2caa39be1");
    assert.equal(thermal.classification, "UNKNOWN");
    assert.equal(thermal.uncertainty_state, "REVIEW_REQUIRED");
    assert.equal(thermal.frp_mw, 24.7);
  });

  it("handles nullable FRP values with sensible fallbacks", () => {
    const backendItem: BackendEventItem = {
      event_id: "evt_null_frp",
      started_at: "2026-08-01T00:00:00Z",
      ended_at: "2026-08-01T00:00:00Z",
      duration_seconds: null,
      centroid_latitude: 10.0,
      centroid_longitude: 20.0,
      detection_count: 1,
      mean_frp_mw: null,
      max_frp_mw: null,
      classification_state: null,
      persistence_state: null,
    };

    const thermal = backendEventToThermalEvent(backendItem);

    assert.equal(thermal.event_id, "evt_null_frp");
    assert.ok(thermal.frp_mw > 0);
    assert.equal(thermal.classification, "UNKNOWN");
    assert.equal(thermal.uncertainty_state, "REVIEW_REQUIRED");
  });
});
