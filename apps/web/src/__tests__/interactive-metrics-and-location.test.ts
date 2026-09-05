import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  formatHumanReadableLocation,
  deriveDistrictFromLocation,
  deriveStateFromLocation,
  filterEventsByLocation,
} from "../lib/location/locationFilter.ts";
import { calculateOperationalRisk } from "../lib/risk/scoring.ts";
import type { ThermalEvent } from "../types/event.ts";

const MOCK_EVENTS: ThermalEvent[] = [
  {
    event_id: "EVT-2026-0831-21",
    latitude: 17.05,
    longitude: 79.27,
    classification: "NON_INDUSTRIAL",
    phenomenon: "vegetation_wildfire",
    uncertainty_state: "CONFIDENT",
    confidence: 0.88,
    frp_mw: 265.0,
    detection_count: 8,
    start_time: "2026-08-31T13:23:00Z",
    end_time: "2026-08-31T13:35:00Z",
    is_persistent: false,
    location_name: "Nalgonda Reserve Forest, Telangana, India",
    context_summary: "Wildfire thermal signature in reserve forest buffer zone",
    satellite_instrument: "VIIRS NOAA-20",
  },
  {
    event_id: "EVT-2026-0831-22",
    latitude: 19.6667,
    longitude: 78.5333,
    classification: "NON_INDUSTRIAL",
    phenomenon: "vegetation_wildfire",
    uncertainty_state: "CONFIDENT",
    confidence: 0.82,
    frp_mw: 68.2,
    detection_count: 5,
    start_time: "2026-08-31T13:08:00Z",
    end_time: "2026-08-31T13:35:00Z",
    is_persistent: false,
    location_name: "Adilabad Forest Range, Telangana, India",
    context_summary: "Moderate dry deciduous forest anomaly cluster under monitoring",
    satellite_instrument: "VIIRS SNPP",
  },
  {
    event_id: "EVT-2026-0831-23",
    latitude: 17.55,
    longitude: 78.48,
    classification: "INDUSTRIAL",
    phenomenon: "FLARE",
    uncertainty_state: "CONFIDENT",
    confidence: 0.95,
    frp_mw: 115.0,
    detection_count: 11,
    start_time: "2026-08-31T09:00:00Z",
    end_time: "2026-08-31T13:30:00Z",
    source_id: "SRC-IND-HYD-001",
    is_persistent: true,
    location_name: "Hyderabad Industrial Corridor, Telangana, India",
    context_summary: "Chemical processing facility flare stack with continuous recurrence",
    satellite_instrument: "MODIS Aqua",
  },
  {
    event_id: "EVT-2026-0831-01",
    latitude: 22.4707,
    longitude: 70.0577,
    classification: "INDUSTRIAL",
    phenomenon: "FLARE",
    uncertainty_state: "CONFIDENT",
    confidence: 0.964,
    frp_mw: 245.8,
    detection_count: 14,
    start_time: "2026-08-31T08:14:22Z",
    end_time: "2026-08-31T13:45:10Z",
    source_id: "SRC-IND-JAM-001",
    is_persistent: true,
    location_name: "Jamnagar Refinery Complex, Gujarat, India",
    context_summary: "Petrochemical refining infrastructure within 320m",
    satellite_instrument: "VIIRS NOAA-20 / SNPP",
  },
];

describe("Interactive Statistics & Location Readability Suite", () => {
  it("Requirement 2: formats human-readable location accurately over raw coordinates", () => {
    const locNalgonda = formatHumanReadableLocation(MOCK_EVENTS[0]);
    assert.equal(locNalgonda, "Nalgonda, Telangana");

    const locAdilabad = formatHumanReadableLocation(MOCK_EVENTS[1]);
    assert.equal(locAdilabad, "Adilabad, Telangana");

    const locHyderabad = formatHumanReadableLocation(MOCK_EVENTS[2]);
    assert.equal(locHyderabad, "Hyderabad, Telangana");

    const locJamnagar = formatHumanReadableLocation(MOCK_EVENTS[3]);
    assert.equal(locJamnagar, "Jamnagar, Gujarat");

    // Generic anomaly string fallback handling
    const genericEvent = {
      location_name: "Thermal Anomaly Cluster (17.05°N, 79.27°E)",
      latitude: 17.05,
      longitude: 79.27,
    };
    const resolvedGeneric = formatHumanReadableLocation(genericEvent);
    assert.ok(
      resolvedGeneric.includes("Telangana") || resolvedGeneric.includes("India"),
      `Expected resolved state/country in: ${resolvedGeneric}`
    );
  });

  it("Requirement 1 - Active Fires: filters to active events in selected scope", () => {
    const telanganaEvents = filterEventsByLocation(MOCK_EVENTS, "India", "Telangana", "ALL");
    assert.equal(telanganaEvents.length, 3);
    assert.deepEqual(
      telanganaEvents.map((e) => e.event_id),
      ["EVT-2026-0831-21", "EVT-2026-0831-22", "EVT-2026-0831-23"]
    );
  });

  it("Requirement 1 - Detected Today: sorts newest detections first", () => {
    const telanganaEvents = filterEventsByLocation(MOCK_EVENTS, "India", "Telangana", "ALL");
    const sorted = [...telanganaEvents].sort(
      (a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime()
    );
    assert.equal(sorted.length, 3);
    assert.equal(sorted[0].event_id, "EVT-2026-0831-21");
  });

  it("Requirement 1 - High / Critical: correctly filters HIGH and CRITICAL severity without merging", () => {
    const telanganaEvents = filterEventsByLocation(MOCK_EVENTS, "India", "Telangana", "ALL");
    const highCritical = telanganaEvents.filter((evt) => {
      const risk = calculateOperationalRisk(evt);
      return risk.level === "CRITICAL" || risk.level === "HIGH";
    });

    assert.ok(highCritical.length >= 1);
    const severities = highCritical.map((e) => calculateOperationalRisk(e).level);
    assert.ok(severities.includes("HIGH") || severities.includes("CRITICAL"));
  });

  it("Requirement 1 - Regions Affected: computes district concentration accurately", () => {
    const telanganaEvents = filterEventsByLocation(MOCK_EVENTS, "India", "Telangana", "ALL");
    const map = new Map<string, number>();
    telanganaEvents.forEach((evt) => {
      const dist = deriveDistrictFromLocation(evt.location_name) || "Other";
      map.set(dist, (map.get(dist) || 0) + 1);
    });

    assert.equal(map.get("Nalgonda"), 1);
    assert.equal(map.get("Adilabad"), 1);
    assert.equal(map.get("Hyderabad"), 1);
    assert.equal(map.size, 3);
  });

  it("Requirement 1 - Peak Intensity: identifies highest FRP event in current scope", () => {
    const telanganaEvents = filterEventsByLocation(MOCK_EVENTS, "India", "Telangana", "ALL");
    const peak = [...telanganaEvents].sort((a, b) => b.frp_mw - a.frp_mw)[0];

    assert.equal(peak.event_id, "EVT-2026-0831-21");
    assert.equal(peak.frp_mw, 265.0);
    assert.equal(formatHumanReadableLocation(peak), "Nalgonda, Telangana");
  });
});
