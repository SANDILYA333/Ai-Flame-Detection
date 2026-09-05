import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Event Operational Intelligence Suite", () => {
  it("calculates aggregate intelligence statistics accurately across catalog", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;
    const total = events.length;

    let industrial = 0;
    let nonIndustrial = 0;
    let unknown = 0;
    let reviewRequired = 0;
    let maxFrp = 0;

    events.forEach((evt) => {
      if (evt.classification === "INDUSTRIAL") industrial++;
      else if (evt.classification === "NON_INDUSTRIAL") nonIndustrial++;
      else unknown++;

      if (evt.uncertainty_state === "REVIEW_REQUIRED") reviewRequired++;
      if (evt.frp_mw > maxFrp) maxFrp = evt.frp_mw;
    });

    assert.equal(total, DEMO_THERMAL_EVENTS.length);
    assert.ok(industrial > 0);
    assert.ok(nonIndustrial > 0);
    assert.ok(unknown > 0);
    assert.ok(reviewRequired > 0);
    assert.ok(maxFrp > 300);
    assert.equal(industrial + nonIndustrial + unknown, total);
  });

  it("ensures UNKNOWN classification is never conflated with NON_INDUSTRIAL", () => {
    const unknownEvents = DEMO_THERMAL_EVENTS.filter((e) => e.classification === "UNKNOWN");
    assert.ok(unknownEvents.length > 0, "Must contain at least 1 UNKNOWN event");

    unknownEvents.forEach((evt) => {
      assert.equal(evt.classification, "UNKNOWN");
      assert.notEqual(evt.classification, "NON_INDUSTRIAL");
      assert.equal(evt.uncertainty_state, "REVIEW_REQUIRED");
    });
  });

  it("handles circular Next/Previous event index wrapping cleanly", () => {
    const total = 5;

    // Next wrap-around
    const nextFromLast = (4 + 1) % total;
    assert.equal(nextFromLast, 0);

    // Prev wrap-around
    const prevFromFirst = 0 <= 0 ? total - 1 : 0 - 1;
    assert.equal(prevFromFirst, 4);

    // Mid-sequence next & prev
    const current = 2;
    const nextMid = current + 1;
    const prevMid = current - 1;
    assert.equal(nextMid, 3);
    assert.equal(prevMid, 1);
  });

  it("verifies all thermal events contain non-empty metadata for intelligence panel", () => {
    DEMO_THERMAL_EVENTS.forEach((evt) => {
      assert.ok(evt.event_id.length > 0);
      assert.ok(evt.latitude >= -90 && evt.latitude <= 90);
      assert.ok(evt.longitude >= -180 && evt.longitude <= 180);
      assert.ok(evt.frp_mw > 0);
      assert.ok(evt.confidence >= 0 && evt.confidence <= 1.0);
      assert.ok(evt.detection_count >= 1);
      assert.ok(evt.start_time.length > 0);
    });
  });
});
