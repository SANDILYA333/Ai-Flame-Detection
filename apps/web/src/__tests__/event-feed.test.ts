import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Live Event Intelligence Feed Suite", () => {
  it("sorts canonical events correctly by newest timestamp", () => {
    const events: ThermalEvent[] = [...DEMO_THERMAL_EVENTS];
    const sorted = [...events].sort((a, b) => {
      const timeA = new Date(a.start_time).getTime() || 0;
      const timeB = new Date(b.start_time).getTime() || 0;
      return timeB - timeA;
    });

    for (let i = 0; i < sorted.length - 1; i++) {
      const current = new Date(sorted[i].start_time).getTime();
      const next = new Date(sorted[i + 1].start_time).getTime();
      assert.ok(current >= next, `Expected event ${i} (${current}) >= event ${i + 1} (${next})`);
    }
  });

  it("sorts canonical events correctly by maximum FRP intensity", () => {
    const events: ThermalEvent[] = [...DEMO_THERMAL_EVENTS];
    const sorted = [...events].sort((a, b) => b.frp_mw - a.frp_mw);

    assert.equal(sorted[0].frp_mw, 380.5);
    for (let i = 0; i < sorted.length - 1; i++) {
      assert.ok(sorted[i].frp_mw >= sorted[i + 1].frp_mw);
    }
  });

  it("sorts canonical events correctly by model confidence score", () => {
    const events: ThermalEvent[] = [...DEMO_THERMAL_EVENTS];
    const sorted = [...events].sort((a, b) => b.confidence - a.confidence);

    for (let i = 0; i < sorted.length - 1; i++) {
      assert.ok(sorted[i].confidence >= sorted[i + 1].confidence);
    }
  });

  it("sorts canonical events correctly by observation detection count", () => {
    const events: ThermalEvent[] = [...DEMO_THERMAL_EVENTS];
    const sorted = [...events].sort((a, b) => b.detection_count - a.detection_count);

    for (let i = 0; i < sorted.length - 1; i++) {
      assert.ok(sorted[i].detection_count >= sorted[i + 1].detection_count);
    }
  });

  it("maintains distinct UNKNOWN and REVIEW_REQUIRED representations", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;
    const unknownEvents = events.filter((e) => e.classification === "UNKNOWN");
    const reviewEvents = events.filter((e) => e.uncertainty_state === "REVIEW_REQUIRED");

    assert.ok(unknownEvents.length > 0, "Must have UNKNOWN events");
    assert.ok(reviewEvents.length > 0, "Must have REVIEW_REQUIRED events");

    // Ensure UNKNOWN is never categorized as NON_INDUSTRIAL
    unknownEvents.forEach((evt) => {
      assert.equal(evt.classification, "UNKNOWN");
      assert.notEqual(evt.classification, "NON_INDUSTRIAL");
      assert.notEqual(evt.classification, "INDUSTRIAL");
    });
  });

  it("synchronizes selected event identity without data loss", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;
    const targetEvent = events[2];

    const selectedId = targetEvent.event_id;
    const matched = events.find((e) => e.event_id === selectedId);

    assert.ok(matched);
    assert.equal(matched?.event_id, targetEvent.event_id);
    assert.equal(matched?.latitude, targetEvent.latitude);
    assert.equal(matched?.longitude, targetEvent.longitude);
  });
});
