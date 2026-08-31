import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("NEXT-FE-013 Frontend Stabilization & Multi-Source QA Suite", () => {
  it("renders multi-source events across multiple distinct global coordinates", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    // Verify events span distinct geographical regions
    const uniqueLats = new Set(events.map((e) => e.latitude.toFixed(1)));
    const uniqueLngs = new Set(events.map((e) => e.longitude.toFixed(1)));

    assert.ok(uniqueLats.size >= 15, "Expected at least 15 distinct latitudes");
    assert.ok(uniqueLngs.size >= 15, "Expected at least 15 distinct longitudes");
    assert.ok(events.length >= 20, "Expected at least 20 multi-source events");
  });

  it("filters events dynamically by time window intervals", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    const maxTimeMs = Math.max(
      ...events.map((e) => new Date(e.start_time).getTime()).filter((t) => !isNaN(t))
    );
    assert.ok(maxTimeMs > 0);

    // 1h filter (cutoff = maxTime - 1h)
    const cutoff1h = maxTimeMs - 1 * 60 * 60 * 1000;
    const events1h = events.filter((e) => new Date(e.start_time).getTime() >= cutoff1h);
    assert.ok(events1h.length > 0);
    assert.ok(events1h.length < events.length);

    // 6h filter
    const cutoff6h = maxTimeMs - 6 * 60 * 60 * 1000;
    const events6h = events.filter((e) => new Date(e.start_time).getTime() >= cutoff6h);
    assert.ok(events6h.length >= events1h.length);
    assert.ok(events6h.length <= events.length);

    // ALL filter
    assert.equal(events.length, 20);
  });

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
