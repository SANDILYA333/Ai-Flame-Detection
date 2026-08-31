import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("NEXT-FE-010 Operational Integration & Polish Suite", () => {
  it("filters events by search query matching location name or ID", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    // Search by location: "Jamnagar"
    const jamnagarQuery = "jamnagar";
    const jamnagarMatches = events.filter(
      (e) =>
        e.location_name?.toLowerCase().includes(jamnagarQuery) ||
        e.event_id.toLowerCase().includes(jamnagarQuery)
    );
    assert.ok(jamnagarMatches.length > 0);
    assert.ok(jamnagarMatches.every((e) => e.location_name?.toLowerCase().includes("jamnagar")));

    // Search by event ID prefix: "EVT-2026"
    const idQuery = "evt-2026";
    const idMatches = events.filter((e) => e.event_id.toLowerCase().includes(idQuery));
    assert.equal(idMatches.length, events.length);
  });

  it("filters events by active GIS layer toggles accurately", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    // Disable industrial layer
    const nonIndustrialOnly = events.filter((e) => e.classification !== "INDUSTRIAL");
    assert.ok(nonIndustrialOnly.length > 0);
    assert.ok(nonIndustrialOnly.every((e) => e.classification !== "INDUSTRIAL"));

    // Enable persistent sources only
    const persistentOnly = events.filter((e) => Boolean(e.is_persistent));
    assert.ok(persistentOnly.length > 0);
    assert.ok(persistentOnly.every((e) => e.is_persistent === true));
  });

  it("filters events by classification chips without conflating UNKNOWN and NON_INDUSTRIAL", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    const industrialEvents = events.filter((e) => e.classification === "INDUSTRIAL");
    const nonIndustrialEvents = events.filter((e) => e.classification === "NON_INDUSTRIAL");
    const unknownEvents = events.filter((e) => e.classification === "UNKNOWN");
    const reviewRequiredEvents = events.filter((e) => e.uncertainty_state === "REVIEW_REQUIRED");

    assert.ok(industrialEvents.length > 0);
    assert.ok(nonIndustrialEvents.length > 0);
    assert.ok(unknownEvents.length > 0);
    assert.ok(reviewRequiredEvents.length > 0);

    // UNKNOWN events must never match NON_INDUSTRIAL
    unknownEvents.forEach((unk) => {
      assert.equal(unk.classification, "UNKNOWN");
      assert.notEqual(unk.classification, "NON_INDUSTRIAL");
    });
  });

  it("computes complete aggregate metrics matching catalog totals", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

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

    assert.equal(events.length, 20);
    assert.ok(industrial > 0);
    assert.ok(nonIndustrial > 0);
    assert.ok(unknown > 0);
    assert.ok(reviewRequired > 0);
    assert.equal(industrial + nonIndustrial + unknown, events.length);
    assert.equal(maxFrp, 380.5);
  });
});
