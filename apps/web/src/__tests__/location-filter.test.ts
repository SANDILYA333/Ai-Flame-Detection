import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  deriveStateFromLocation,
  deriveDistrictFromLocation,
  deriveCountryFromLocation,
  filterEventsByLocation,
  extractAvailableLocations,
  STATE_BOUNDS_MAP,
} from "../lib/location/locationFilter.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";

describe("Geographic Hierarchy & Location Filtering Suite", () => {
  it("Step 1: Derives state name accurately from location strings and coordinates", () => {
    assert.equal(deriveStateFromLocation("Nalgonda Forest Fringe, Telangana, India"), "Telangana");
    assert.equal(deriveStateFromLocation("Adilabad Forest Zone, Telangana, India"), "Telangana");
    assert.equal(deriveStateFromLocation("Jamnagar Refinery Complex, Gujarat, India"), "Gujarat");
    assert.equal(deriveStateFromLocation("Singrauli Super Thermal Power Station, MP, India"), "Madhya Pradesh");
    assert.equal(deriveStateFromLocation("Angul-Talcher Industrial Belt, Odisha, India"), "Odisha");
    assert.equal(deriveStateFromLocation("Ludhiana, Punjab, India"), "Punjab");
  });

  it("Step 2: Derives district and city names cleanly", () => {
    assert.equal(deriveDistrictFromLocation("Nalgonda Forest Fringe, Telangana, India"), "Nalgonda");
    assert.equal(deriveDistrictFromLocation("Adilabad Forest Zone, Telangana, India"), "Adilabad");
    assert.equal(deriveDistrictFromLocation("Jamnagar Refinery Complex, Gujarat, India"), "Jamnagar");
    assert.equal(deriveDistrictFromLocation("Angul-Talcher Industrial Belt, Odisha, India"), "Angul");
  });

  it("Step 3: Filters events by Country, State, and District without data loss", () => {
    // 1. All events
    const allEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "ALL", "ALL", "ALL");
    assert.equal(allEvents.length, DEMO_THERMAL_EVENTS.length);

    // 2. India scope
    const indiaEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "ALL", "ALL");
    assert.ok(indiaEvents.length > 0);
    assert.ok(indiaEvents.length <= DEMO_THERMAL_EVENTS.length);

    // 3. Telangana scope
    const telanganaEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "Telangana", "ALL");
    assert.ok(telanganaEvents.length >= 3, "Expected at least 3 events in Telangana");
    telanganaEvents.forEach((e) => {
      assert.ok(
        (e.location_name || "").includes("Telangana") ||
          deriveStateFromLocation(e.location_name) === "Telangana"
      );
    });

    // 4. Nalgonda district scope
    const nalgondaEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "Telangana", "Nalgonda");
    assert.ok(nalgondaEvents.length >= 1, "Expected Nalgonda event");
    assert.ok(nalgondaEvents[0].location_name?.includes("Nalgonda"));
  });

  it("Step 4: Extracts available locations with accurate counts", () => {
    const { countries, states, districts } = extractAvailableLocations(DEMO_THERMAL_EVENTS);
    assert.ok(countries.length > 0);
    assert.ok(states.length > 0);
    assert.ok(districts.length > 0);

    const telanganaEntry = states.find((s) => s.name === "Telangana");
    assert.ok(telanganaEntry, "Telangana should be present in extracted states");
    assert.ok(telanganaEntry.count! >= 3);

    const nalgondaEntry = districts.find((d) => d.name === "Nalgonda");
    assert.ok(nalgondaEntry, "Nalgonda should be present in extracted districts");
  });

  it("Step 5: Verifies canonical State Bounding Boxes exist for key testing regions", () => {
    assert.ok(STATE_BOUNDS_MAP["Telangana"]);
    assert.ok(STATE_BOUNDS_MAP["Gujarat"]);
    assert.ok(STATE_BOUNDS_MAP["Odisha"]);

    const [minLat, minLon, maxLat, maxLon] = STATE_BOUNDS_MAP["Telangana"].bbox;
    assert.ok(minLat < maxLat);
    assert.ok(minLon < maxLon);
  });
});
