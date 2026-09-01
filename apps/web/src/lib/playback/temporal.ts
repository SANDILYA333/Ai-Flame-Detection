import type { ThermalEvent } from "../../types/event.ts";
import type { PlaybackRange, TimeWindow } from "../../types/playback.ts";

/**
 * Derives start_time and end_time ISO query parameters for a selected time window.
 */
export function deriveTimeWindowQuery(
  window: TimeWindow | string,
  referenceTime?: number
): {
  start_time?: string;
  end_time?: string;
  startMs: number;
  endMs: number;
} {
  const normalized = (window || "ALL").toUpperCase() as TimeWindow;
  const endMs = referenceTime ?? Date.now();

  let startMs = endMs;

  switch (normalized) {
    case "1H":
      startMs = endMs - 1 * 60 * 60 * 1000;
      return {
        start_time: new Date(startMs).toISOString(),
        end_time: new Date(endMs).toISOString(),
        startMs,
        endMs,
      };
    case "6H":
      startMs = endMs - 6 * 60 * 60 * 1000;
      return {
        start_time: new Date(startMs).toISOString(),
        end_time: new Date(endMs).toISOString(),
        startMs,
        endMs,
      };
    case "24H":
      startMs = endMs - 24 * 60 * 60 * 1000;
      return {
        start_time: new Date(startMs).toISOString(),
        end_time: new Date(endMs).toISOString(),
        startMs,
        endMs,
      };
    case "48H":
      startMs = endMs - 48 * 60 * 60 * 1000;
      return {
        start_time: new Date(startMs).toISOString(),
        end_time: new Date(endMs).toISOString(),
        startMs,
        endMs,
      };
    case "7D":
      startMs = endMs - 7 * 24 * 60 * 60 * 1000;
      return {
        start_time: new Date(startMs).toISOString(),
        end_time: new Date(endMs).toISOString(),
        startMs,
        endMs,
      };
    case "ALL":
    default:
      return {
        start_time: undefined,
        end_time: undefined,
        startMs: 0,
        endMs,
      };
  }
}

/**
 * Calculates the temporal bounding range (start, end, duration) for a given time window.
 */
export function calculateWindowRange(
  window: TimeWindow | string,
  events: ThermalEvent[],
  referenceTime?: number
): PlaybackRange {
  let minTime = Infinity;
  let maxTime = -Infinity;

  events.forEach((evt) => {
    const tStart = new Date(evt.start_time).getTime();
    if (!isNaN(tStart)) {
      if (tStart < minTime) minTime = tStart;
      if (tStart > maxTime) maxTime = tStart;
    }
    if (evt.end_time) {
      const tEnd = new Date(evt.end_time).getTime();
      if (!isNaN(tEnd) && tEnd > maxTime) {
        maxTime = tEnd;
      }
    }
  });

  const now = referenceTime ?? Date.now();
  // When events exist, anchor to latest event timestamp or reference time
  const end = maxTime !== -Infinity ? maxTime : now;
  const normalizedWindow = (window || "ALL").toUpperCase() as TimeWindow;

  let start = end;

  switch (normalizedWindow) {
    case "1H":
      start = end - 1 * 60 * 60 * 1000;
      break;
    case "6H":
      start = end - 6 * 60 * 60 * 1000;
      break;
    case "24H":
      start = end - 24 * 60 * 60 * 1000;
      break;
    case "48H":
      start = end - 48 * 60 * 60 * 1000;
      break;
    case "7D":
      start = end - 7 * 24 * 60 * 60 * 1000;
      break;
    case "ALL":
    default:
      start = minTime !== Infinity ? minTime : end - 24 * 60 * 60 * 1000;
      break;
  }

  // Ensure start <= end with non-zero duration
  if (start >= end) {
    start = end - 1 * 60 * 60 * 1000;
  }

  return {
    start,
    end,
    durationMs: end - start,
  };
}

/**
 * Filters a collection of thermal events according to interval intersection logic:
 * An event with interval [startTime, endTime] is included if it overlaps the active window
 * [range.start, activeEnd], where activeEnd is (isPlaybackActive ? playbackTime : range.end).
 */
export function filterEventsByTemporalState(
  events: ThermalEvent[],
  range: PlaybackRange,
  playbackTime: number,
  isPlaybackActive: boolean
): ThermalEvent[] {
  return events.filter((evt) => {
    const startTime = new Date(evt.start_time).getTime();
    if (isNaN(startTime)) return true;

    const endTime = evt.end_time ? new Date(evt.end_time).getTime() : startTime;
    const validEndTime = isNaN(endTime) ? startTime : Math.max(startTime, endTime);

    const activeEnd = isPlaybackActive ? playbackTime : range.end;

    // Interval Intersection Math:
    // Event interval [startTime, validEndTime] overlaps [range.start, activeEnd]
    // iff startTime <= activeEnd AND validEndTime >= range.start
    if (startTime > activeEnd) {
      return false;
    }
    if (validEndTime < range.start) {
      return false;
    }

    return true;
  });
}

/**
 * Formats a timestamp into human-readable short timeline date/time (UTC).
 */
export function formatTimelineStamp(timestampMs: number): string {
  if (isNaN(timestampMs) || timestampMs <= 0) return "--:--";
  const d = new Date(timestampMs);
  const hours = String(d.getUTCHours()).padStart(2, "0");
  const minutes = String(d.getUTCMinutes()).padStart(2, "0");
  const seconds = String(d.getUTCSeconds()).padStart(2, "0");
  return `${hours}:${minutes}:${seconds} UTC`;
}

/**
 * Formats a short month/day label for timeline axis endpoints.
 */
export function formatTimelineAxisLabel(timestampMs: number): string {
  if (isNaN(timestampMs) || timestampMs <= 0) return "--:--";
  const d = new Date(timestampMs);
  const month = d.toLocaleString("en-US", { month: "short", timeZone: "UTC" });
  const day = d.getUTCDate();
  const hours = String(d.getUTCHours()).padStart(2, "0");
  const minutes = String(d.getUTCMinutes()).padStart(2, "0");
  return `${month} ${day} ${hours}:${minutes}`;
}
