import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateWindowRange,
  deriveTimeWindowQuery,
  filterEventsByTemporalState,
  formatTimelineStamp,
  formatTimelineAxisLabel,
} from "../lib/playback/temporal.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";
import type { PlaybackRange } from "../types/playback.ts";

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

  it("derives deterministic ISO query parameters for 1H, 6H, 24H, 48H, 7D, and ALL", () => {
    const fixedNow = new Date("2026-08-31T12:00:00.000Z").getTime();

    const q1H = deriveTimeWindowQuery("1H", fixedNow);
    assert.equal(q1H.start_time, "2026-08-31T11:00:00.000Z");
    assert.equal(q1H.end_time, "2026-08-31T12:00:00.000Z");

    const q6H = deriveTimeWindowQuery("6H", fixedNow);
    assert.equal(q6H.start_time, "2026-08-31T06:00:00.000Z");
    assert.equal(q6H.end_time, "2026-08-31T12:00:00.000Z");

    const q24H = deriveTimeWindowQuery("24H", fixedNow);
    assert.equal(q24H.start_time, "2026-08-30T12:00:00.000Z");
    assert.equal(q24H.end_time, "2026-08-31T12:00:00.000Z");

    const q48H = deriveTimeWindowQuery("48H", fixedNow);
    assert.equal(q48H.start_time, "2026-08-29T12:00:00.000Z");

    const q7D = deriveTimeWindowQuery("7D", fixedNow);
    assert.equal(q7D.start_time, "2026-08-24T12:00:00.000Z");

    const qAll = deriveTimeWindowQuery("ALL", fixedNow);
    assert.equal(qAll.start_time, undefined);
    assert.equal(qAll.end_time, undefined);
  });

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
  });

  it("filters events correctly in LIVE mode based on interval overlap", () => {
    const range1H = calculateWindowRange("1H", mockEvents);
    const visible1H = filterEventsByTemporalState(mockEvents, range1H, range1H.end, false);
    // 1H window covers 11:30 - 12:30 -> EVT-T3 (11:30-12:00) and EVT-T4 (12:00-12:30)
    assert.equal(visible1H.length, 2);
    assert.ok(visible1H.some((e) => e.event_id === "EVT-T3"));
    assert.ok(visible1H.some((e) => e.event_id === "EVT-T4"));

    const range6H = calculateWindowRange("6H", mockEvents);
    const visible6H = filterEventsByTemporalState(mockEvents, range6H, range6H.end, false);
    assert.equal(visible6H.length, 4);
  });

  it("correctly includes ongoing events that started before the window but overlap it", () => {
    const ongoingEvent: ThermalEvent = {
      event_id: "EVT-ONGOING",
      latitude: 22.0,
      longitude: 70.0,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.95,
      uncertainty_state: "CONFIDENT",
      frp_mw: 300.0,
      detection_count: 5,
      is_persistent: true,
      start_time: "2026-08-31T08:00:00Z", // Started 4 hours ago
      end_time: "2026-08-31T12:15:00Z",   // Active until 12:15 (inside 1H window 11:30-12:30)
    };

    const range1H: PlaybackRange = {
      start: new Date("2026-08-31T11:30:00Z").getTime(),
      end: new Date("2026-08-31T12:30:00Z").getTime(),
      durationMs: 3600000,
    };

    const visible = filterEventsByTemporalState([ongoingEvent], range1H, range1H.end, false);
    assert.equal(visible.length, 1, "Ongoing fire overlapping window must be VISIBLE");
    assert.equal(visible[0].event_id, "EVT-ONGOING");
  });

  it("correctly excludes completely old events that ended before the window", () => {
    const oldEvent: ThermalEvent = {
      event_id: "EVT-OLD",
      latitude: 22.0,
      longitude: 70.0,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.95,
      uncertainty_state: "CONFIDENT",
      frp_mw: 50.0,
      detection_count: 1,
      is_persistent: false,
      start_time: "2026-08-31T08:00:00Z",
      end_time: "2026-08-31T09:00:00Z", // Ended at 09:00 (before 11:30)
    };

    const range1H: PlaybackRange = {
      start: new Date("2026-08-31T11:30:00Z").getTime(),
      end: new Date("2026-08-31T12:30:00Z").getTime(),
      durationMs: 3600000,
    };

    const visible = filterEventsByTemporalState([oldEvent], range1H, range1H.end, false);
    assert.equal(visible.length, 0, "Event ending before window must be HIDDEN");
  });

  it("filters events progressively in PLAYBACK mode at specific playhead timestamps", () => {
    const range6H = calculateWindowRange("6H", mockEvents);
    const playheadTime = new Date("2026-08-31T10:30:00Z").getTime();

    const visibleAt1030 = filterEventsByTemporalState(mockEvents, range6H, playheadTime, true);

    assert.equal(visibleAt1030.length, 2);
    assert.ok(visibleAt1030.some((e) => e.event_id === "EVT-T1"));
    assert.ok(visibleAt1030.some((e) => e.event_id === "EVT-T2"));
    assert.ok(!visibleAt1030.some((e) => e.event_id === "EVT-T3"));
    assert.ok(!visibleAt1030.some((e) => e.event_id === "EVT-T4"));
  });

  it("guarantees 2D Map and 3D Globe receive identical canonical event datasets", () => {
    const range24H = calculateWindowRange("24H", mockEvents);
    const map2DEvents = filterEventsByTemporalState(mockEvents, range24H, range24H.end, false);
    const globe3DEvents = filterEventsByTemporalState(mockEvents, range24H, range24H.end, false);

    assert.equal(map2DEvents.length, globe3DEvents.length);
    for (let i = 0; i < map2DEvents.length; i++) {
      assert.equal(map2DEvents[i].event_id, globe3DEvents[i].event_id);
    }
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
