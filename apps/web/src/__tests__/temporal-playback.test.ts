import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateWindowRange,
  filterEventsByTemporalState,
  formatTimelineStamp,
  formatTimelineAxisLabel,
} from "../lib/playback/temporal.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Temporal Playback & Time Window Suite", () => {
  const mockEvents: ThermalEvent[] = [
    {
      event_id: "EVT-T1",
      latitude: 22.0,
      longitude: 70.0,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.95,
      uncertainty_state: "CONFIDENT",
      frp_mw: 150.0,
      detection_count: 3,
      is_persistent: true,
      start_time: "2026-08-31T06:00:00Z", // 6 hours before 12:00
      end_time: "2026-08-31T07:00:00Z",
    },
    {
      event_id: "EVT-T2",
      latitude: 23.0,
      longitude: 71.0,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.90,
      uncertainty_state: "CONFIDENT",
      frp_mw: 200.0,
      detection_count: 2,
      is_persistent: true,
      start_time: "2026-08-31T10:00:00Z", // 2 hours before 12:00
      end_time: "2026-08-31T11:00:00Z",
    },
    {
      event_id: "EVT-T3",
      latitude: 24.0,
      longitude: 72.0,
      phenomenon: "OPEN_BURNING",
      classification: "NON_INDUSTRIAL",
      confidence: 0.85,
      uncertainty_state: "CONFIDENT",
      frp_mw: 30.0,
      detection_count: 1,
      is_persistent: false,
      start_time: "2026-08-31T11:30:00Z", // 30 min before 12:00
      end_time: "2026-08-31T12:00:00Z",
    },
    {
      event_id: "EVT-T4",
      latitude: 25.0,
      longitude: 73.0,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.92,
      uncertainty_state: "CONFIDENT",
      frp_mw: 180.0,
      detection_count: 2,
      is_persistent: true,
      start_time: "2026-08-31T12:00:00Z", // Latest (Reference)
      end_time: "2026-08-31T12:30:00Z",
    },
  ];

  it("calculates accurate time window ranges for 1H, 6H, 24H, 48H, 7D, ALL", () => {
    const range1H = calculateWindowRange("1H", mockEvents);
    assert.equal(range1H.durationMs, 1 * 60 * 60 * 1000);

    const range6H = calculateWindowRange("6H", mockEvents);
    assert.equal(range6H.durationMs, 6 * 60 * 60 * 1000);

    const range24H = calculateWindowRange("24H", mockEvents);
    assert.equal(range24H.durationMs, 24 * 60 * 60 * 1000);

    const range48H = calculateWindowRange("48H", mockEvents);
    assert.equal(range48H.durationMs, 48 * 60 * 60 * 1000);

    const range7D = calculateWindowRange("7D", mockEvents);
    assert.equal(range7D.durationMs, 7 * 24 * 60 * 60 * 1000);

    const rangeAll = calculateWindowRange("ALL", mockEvents);
    assert.ok(rangeAll.durationMs > 0);
    assert.equal(rangeAll.end, new Date("2026-08-31T12:00:00Z").getTime());
    assert.equal(rangeAll.start, new Date("2026-08-31T06:00:00Z").getTime());
  });

  it("filters events correctly in LIVE mode based on time window", () => {
    const range1H = calculateWindowRange("1H", mockEvents);
    const visible1H = filterEventsByTemporalState(mockEvents, range1H, range1H.end, false);
    // 1H window covers 11:00 to 12:00 -> EVT-T3 (11:30) and EVT-T4 (12:00)
    assert.equal(visible1H.length, 2);
    assert.ok(visible1H.some((e) => e.event_id === "EVT-T3"));
    assert.ok(visible1H.some((e) => e.event_id === "EVT-T4"));

    const range6H = calculateWindowRange("6H", mockEvents);
    const visible6H = filterEventsByTemporalState(mockEvents, range6H, range6H.end, false);
    // 6H window covers 06:00 to 12:00 -> all 4 events
    assert.equal(visible6H.length, 4);
  });

  it("filters events progressively in PLAYBACK mode at specific playhead timestamps", () => {
    const range6H = calculateWindowRange("6H", mockEvents);
    const playheadTime = new Date("2026-08-31T10:30:00Z").getTime();

    // At 10:30, events before or at 10:30 (EVT-T1 @ 06:00 and EVT-T2 @ 10:00) must appear.
    // EVT-T3 @ 11:30 and EVT-T4 @ 12:00 must NOT appear yet.
    const visibleAt1030 = filterEventsByTemporalState(mockEvents, range6H, playheadTime, true);

    assert.equal(visibleAt1030.length, 2);
    assert.ok(visibleAt1030.some((e) => e.event_id === "EVT-T1"));
    assert.ok(visibleAt1030.some((e) => e.event_id === "EVT-T2"));
    assert.ok(!visibleAt1030.some((e) => e.event_id === "EVT-T3"));
    assert.ok(!visibleAt1030.some((e) => e.event_id === "EVT-T4"));
  });

  it("includes boundary events matching exact playhead timestamp", () => {
    const range6H = calculateWindowRange("6H", mockEvents);
    const exactT2Time = new Date("2026-08-31T10:00:00Z").getTime();

    const visible = filterEventsByTemporalState(mockEvents, range6H, exactT2Time, true);

    assert.equal(visible.length, 2);
    assert.ok(visible.some((e) => e.event_id === "EVT-T2"));
  });

  it("handles empty windows and catalogs without errors", () => {
    const range = calculateWindowRange("1H", []);
    assert.ok(range.start < range.end);
    assert.equal(range.durationMs, 3600000);

    const filtered = filterEventsByTemporalState([], range, range.end, false);
    assert.equal(filtered.length, 0);
  });

  it("formats timeline labels and timestamps into standard human-readable formats", () => {
    const ts = new Date("2026-08-31T14:32:05Z").getTime();

    const stamp = formatTimelineStamp(ts);
    assert.equal(stamp, "14:32:05 UTC");

    const axisLabel = formatTimelineAxisLabel(ts);
    assert.ok(axisLabel.includes("Aug 31"));
    assert.ok(axisLabel.includes("14:32"));
  });

  it("ensures zero modification to original backend event timestamps", () => {
    const events = DEMO_THERMAL_EVENTS;
    const initialTimestamps = events.map((e) => e.start_time);

    const range = calculateWindowRange("24H", events);
    filterEventsByTemporalState(events, range, range.start + 1000, true);

    events.forEach((e, idx) => {
      assert.equal(e.start_time, initialTimestamps[idx]);
    });
  });
});
