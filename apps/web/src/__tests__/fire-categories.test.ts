import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  FIRE_CATEGORIES,
  isEventInCategory,
  derivePrimaryCategory,
  computeCategoryMetrics,
} from "../lib/categories/fireCategories.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";

describe("Fire Categories & Discovery Metrics Suite", () => {
  it("Step 1: All 6 required domain categories are defined with valid metadata", () => {
    assert.equal(FIRE_CATEGORIES.length, 6);
    const expectedIds = [
      "WILDFIRE",
      "INDUSTRIAL",
      "HOTSPOT",
      "PERSISTENT",
      "AGRICULTURAL",
      "REVIEW_REQUIRED",
    ];
    expectedIds.forEach((id) => {
      const found = FIRE_CATEGORIES.find((c) => c.id === id);
      assert.ok(found, `Category ${id} should be defined`);
      assert.ok(found.title.length > 0);
      assert.ok(found.description.length > 0);
    });
  });

  it("Step 2: Correctly matches Wildfires and Forest Fires", () => {
    const nalgondaEvent = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Nalgonda"));
    assert.ok(nalgondaEvent, "Nalgonda event should exist");
    assert.ok(
      isEventInCategory(nalgondaEvent, "WILDFIRE"),
      "Nalgonda forest event should be recognized as WILDFIRE"
    );

    const jamnagarRefinery = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Jamnagar"));
    assert.ok(jamnagarRefinery);
    assert.equal(
      isEventInCategory(jamnagarRefinery, "WILDFIRE"),
      false,
      "Refinery flare must NOT be categorized as wildfire"
    );
  });

  it("Step 3: Correctly matches Industrial and Facility Fires", () => {
    const jamnagarRefinery = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Jamnagar"));
    assert.ok(jamnagarRefinery);
    assert.ok(isEventInCategory(jamnagarRefinery, "INDUSTRIAL"));

    const singrauliPower = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Singrauli"));
    assert.ok(singrauliPower);
    assert.ok(isEventInCategory(singrauliPower, "INDUSTRIAL"));
  });

  it("Step 4: Preserves UNKNOWN != NON_INDUSTRIAL invariant for Uncertain / Review Required", () => {
    const unknownEvent = DEMO_THERMAL_EVENTS.find((e) => e.classification === "UNKNOWN");
    if (unknownEvent) {
      assert.ok(isEventInCategory(unknownEvent, "REVIEW_REQUIRED"));
      assert.equal(isEventInCategory(unknownEvent, "INDUSTRIAL"), false);
      assert.equal(derivePrimaryCategory(unknownEvent), "REVIEW_REQUIRED");
    }
  });

  it("Step 5: Computes live category metrics dynamically from events catalog", () => {
    const metrics = computeCategoryMetrics(DEMO_THERMAL_EVENTS);
    assert.ok(metrics.ALL.totalCount === DEMO_THERMAL_EVENTS.length);
    assert.ok(metrics.WILDFIRE.totalCount > 0);
    assert.ok(metrics.INDUSTRIAL.totalCount > 0);
    assert.ok(metrics.HOTSPOT.totalCount > 0);
    assert.ok(metrics.PERSISTENT.totalCount > 0);
    assert.ok(metrics.ALL.maxFrp > 0);
  });
});
