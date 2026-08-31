import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";

describe("Deterministic Thermal Events Fixture Suite", () => {
  test("contains a valid non-empty catalog of thermal events", () => {
    assert.ok(Array.isArray(DEMO_THERMAL_EVENTS));
    assert.ok(DEMO_THERMAL_EVENTS.length >= 15);
  });

  test("all events have valid WGS-84 geographic coordinates", () => {
    for (const evt of DEMO_THERMAL_EVENTS) {
      assert.ok(typeof evt.latitude === "number");
      assert.ok(typeof evt.longitude === "number");
      assert.ok(evt.latitude >= -90 && evt.latitude <= 90, `Invalid latitude in ${evt.event_id}`);
      assert.ok(evt.longitude >= -180 && evt.longitude <= 180, `Invalid longitude in ${evt.event_id}`);
    }
  });

  test("all events have valid FRP and confidence values", () => {
    for (const evt of DEMO_THERMAL_EVENTS) {
      assert.ok(evt.frp_mw > 0, `FRP must be positive in ${evt.event_id}`);
      assert.ok(evt.confidence >= 0 && evt.confidence <= 1, `Confidence must be [0,1] in ${evt.event_id}`);
      assert.ok(evt.detection_count >= 1, `Detection count must be >= 1 in ${evt.event_id}`);
    }
  });

  test("covers all 3 orthogonal classification states: INDUSTRIAL, NON_INDUSTRIAL, UNKNOWN", () => {
    const classifications = new Set(DEMO_THERMAL_EVENTS.map((e) => e.classification));
    assert.ok(classifications.has("INDUSTRIAL"), "Must include INDUSTRIAL events");
    assert.ok(classifications.has("NON_INDUSTRIAL"), "Must include NON_INDUSTRIAL events");
    assert.ok(classifications.has("UNKNOWN"), "Must include UNKNOWN events");
  });

  test("covers REVIEW_REQUIRED and CONFIDENT uncertainty states", () => {
    const uncertaintyStates = new Set(DEMO_THERMAL_EVENTS.map((e) => e.uncertainty_state));
    assert.ok(uncertaintyStates.has("CONFIDENT"), "Must include CONFIDENT events");
    assert.ok(uncertaintyStates.has("REVIEW_REQUIRED"), "Must include REVIEW_REQUIRED events");
  });

  test("contains valid ISO timestamps", () => {
    for (const evt of DEMO_THERMAL_EVENTS) {
      assert.ok(!isNaN(Date.parse(evt.start_time)), `Invalid start_time in ${evt.event_id}`);
      assert.ok(!isNaN(Date.parse(evt.end_time)), `Invalid end_time in ${evt.event_id}`);
      assert.ok(new Date(evt.end_time) >= new Date(evt.start_time), `end_time before start_time in ${evt.event_id}`);
    }
  });
});
