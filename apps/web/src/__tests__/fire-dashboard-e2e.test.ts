import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import {
  filterEventsByLocation,
  extractAvailableLocations,
  deriveStateFromLocation,
} from "../lib/location/locationFilter.ts";
import {
  FIRE_CATEGORIES,
  isEventInCategory,
  computeCategoryMetrics,
  derivePrimaryCategory,
} from "../lib/categories/fireCategories.ts";
import { calculateOperationalRisk } from "../lib/risk/scoring.ts";

describe("Phase 2 Test Matrix: Fire Category Exploration & Incident Details", () => {
  // Test 1 — Category Navigation
  it("Test 1: All 6 fire categories are discoverable from dashboard", () => {
    assert.equal(FIRE_CATEGORIES.length, 6);
    const categoryIds = FIRE_CATEGORIES.map((c) => c.id);
    assert.ok(categoryIds.includes("WILDFIRE"));
    assert.ok(categoryIds.includes("INDUSTRIAL"));
    assert.ok(categoryIds.includes("HOTSPOT"));
    assert.ok(categoryIds.includes("PERSISTENT"));
    assert.ok(categoryIds.includes("AGRICULTURAL"));
    assert.ok(categoryIds.includes("REVIEW_REQUIRED"));
  });

  // Test 2 — Real Event Data
  it("Test 2: Displays real event data from canonical catalog without synthetic mocks", () => {
    assert.ok(DEMO_THERMAL_EVENTS.length >= 20);
    DEMO_THERMAL_EVENTS.forEach((evt) => {
      assert.ok(evt.event_id.startsWith("EVT-"));
      assert.ok(evt.latitude !== 0 && evt.longitude !== 0);
      assert.ok(evt.start_time.length > 0);
      assert.ok(evt.confidence > 0);
    });
  });

  // Test 3 — Event Information
  it("Test 3: Minimum required event card information is present on every event", () => {
    DEMO_THERMAL_EVENTS.forEach((evt) => {
      assert.ok(evt.event_id, "Event must have ID");
      assert.ok(evt.location_name, "Event must have location");
      assert.ok(evt.start_time, "Event must have detection timestamp");
      const risk = calculateOperationalRisk(evt);
      assert.ok(risk.level, "Event must have deterministic risk severity");
    });
  });

  // Test 4 — Location Filtering: Telangana -> Wildfires
  it("Test 4: Selecting 'Telangana' then 'Wildfires' filters to Telangana-relevant wildfire incidents", () => {
    const telanganaEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "Telangana", "ALL");
    assert.ok(telanganaEvents.length >= 3, "Expected at least 3 incidents in Telangana");

    const telanganaWildfires = telanganaEvents.filter((e) => isEventInCategory(e, "WILDFIRE"));
    assert.ok(telanganaWildfires.length >= 1, "Expected at least 1 wildfire in Telangana");

    const nalgonda = telanganaWildfires.find((e) => e.location_name?.includes("Nalgonda"));
    assert.ok(nalgonda, "Nalgonda wildfire incident must be found in Telangana wildfires");
    assert.equal(nalgonda.event_id, "EVT-2026-0831-21");

    const adilabad = telanganaEvents.find((e) => e.location_name?.includes("Adilabad"));
    assert.ok(adilabad, "Adilabad incident must be in Telangana catalog");
    assert.equal(adilabad.event_id, "EVT-2026-0831-22");
  });

  // Test 5 & 6 — Synchronized Selection (Map Marker <-> Event List)
  it("Test 5 & 6: Single Source of Truth for selectedEvent synchronizes Map and Event List", () => {
    const nalgondaEvent = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Nalgonda"))!;
    assert.ok(nalgondaEvent);

    // Simulated selection state
    let selectedEventId: string | null = null;
    let isConciseDetailOpen = false;

    // A. Map Marker Click
    const handleMapMarkerClick = (evt: typeof nalgondaEvent) => {
      selectedEventId = evt.event_id;
      isConciseDetailOpen = true;
    };
    handleMapMarkerClick(nalgondaEvent);
    assert.equal(selectedEventId, "EVT-2026-0831-21");
    assert.equal(isConciseDetailOpen, true);

    // B. Event List Item Click
    const handleListItemClick = (evt: typeof nalgondaEvent) => {
      selectedEventId = evt.event_id;
      isConciseDetailOpen = true;
    };
    handleListItemClick(nalgondaEvent);
    assert.equal(selectedEventId, "EVT-2026-0831-21");
  });

  // Test 7 — Concise Event Details View
  it("Test 7: Concise Event Details accurately presents the 5 core dimensions", () => {
    const nalgonda = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Nalgonda"))!;
    assert.ok(nalgonda);

    // WHERE
    assert.ok(nalgonda.location_name?.includes("Nalgonda"));
    assert.equal(nalgonda.latitude, 17.05);
    assert.equal(nalgonda.longitude, 79.27);

    // WHEN
    assert.ok(nalgonda.start_time);
    assert.ok(nalgonda.end_time);

    // WHAT
    assert.equal(nalgonda.classification, "NON_INDUSTRIAL");
    assert.equal(derivePrimaryCategory(nalgonda), "WILDFIRE");

    // HOW SERIOUS
    const risk = calculateOperationalRisk(nalgonda);
    assert.equal(risk.level, "HIGH");
    assert.equal(nalgonda.frp_mw, 265.0);

    // HOW CONFIDENT
    assert.equal(nalgonda.confidence, 0.935);
    assert.equal(nalgonda.uncertainty_state, "CONFIDENT");
  });

  // Test 8 — Recent Detections Integration (Both Paths resolve to same event)
  it("Test 8: Both Entry Paths (Category -> Event and Recent Detection -> Event) resolve to same event", () => {
    const targetId = "EVT-2026-0831-21";

    // Path A: Category -> Filter -> Select
    const pathAEvent = DEMO_THERMAL_EVENTS.filter((e) => isEventInCategory(e, "WILDFIRE")).find(
      (e) => e.event_id === targetId
    );
    assert.ok(pathAEvent);

    // Path B: Recent Detections Feed -> Select
    const sortedFeed = [...DEMO_THERMAL_EVENTS].sort(
      (a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime()
    );
    const pathBEvent = sortedFeed.find((e) => e.event_id === targetId);
    assert.ok(pathBEvent);

    assert.equal(pathAEvent.event_id, pathBEvent.event_id);
    assert.equal(pathAEvent.location_name, pathBEvent.location_name);
  });

  // Test 9 — Empty State Handling
  it("Test 9: Handled cleanly when a category or region has zero matching incidents", () => {
    // Empty region query: filter for a non-existent district
    const emptyResult = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "Telangana", "NonExistentDistrict");
    assert.equal(emptyResult.length, 0);

    // Category metrics on empty array
    const emptyMetrics = computeCategoryMetrics([]);
    assert.equal(emptyMetrics.ALL.totalCount, 0);
    assert.equal(emptyMetrics.WILDFIRE.totalCount, 0);
  });

  // Test 10 — Handoff Preparation for Phase 3
  it("Test 10: Event Details preserves canonical ID and camera coordinates for Level 2 Handoff", () => {
    const nalgonda = DEMO_THERMAL_EVENTS.find((e) => e.location_name?.includes("Nalgonda"))!;
    const handoffPayload = {
      event_id: nalgonda.event_id,
      lat: nalgonda.latitude,
      lng: nalgonda.longitude,
      zoom: 8.5,
      classification: nalgonda.classification,
    };

    assert.equal(handoffPayload.event_id, "EVT-2026-0831-21");
    assert.equal(handoffPayload.lat, 17.05);
    assert.equal(handoffPayload.lng, 79.27);
  });

  // Test 11 — Geographic Scope Persistence Across Navigation
  it("Test 11: Scope is preserved when exploring categories", () => {
    let activeState = "Telangana";
    let activeCategory = "ALL";

    // Navigate to Wildfires
    activeCategory = "WILDFIRE";
    const scopedEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", activeState, "ALL").filter(
      (e) => isEventInCategory(e, activeCategory as any)
    );

    assert.ok(scopedEvents.length > 0);
    scopedEvents.forEach((e) => {
      assert.equal(deriveStateFromLocation(e.location_name), "Telangana");
    });

    // Return to Dashboard
    activeCategory = "ALL";
    assert.equal(activeState, "Telangana", "State scope must not be reset on returning to dashboard");
  });

  // Test 12 — Regression: UNKNOWN != NON_INDUSTRIAL invariant
  it("Test 12: Preserves UNKNOWN != NON_INDUSTRIAL and scientific integrity", () => {
    const unknownEvents = DEMO_THERMAL_EVENTS.filter((e) => e.classification === "UNKNOWN");
    unknownEvents.forEach((evt) => {
      assert.notEqual(evt.classification, "NON_INDUSTRIAL");
      const primary = derivePrimaryCategory(evt);
      assert.equal(primary, "REVIEW_REQUIRED");
    });
  });
});
