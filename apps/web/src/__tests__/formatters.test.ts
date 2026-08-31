import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { formatCoordinate } from "../lib/format/coordinates.ts";
import { formatFrp, formatPercent, formatCompactCount } from "../lib/format/numbers.ts";
import { formatUtcTime, formatUtcDateTime, formatRelativeSecondsAgo } from "../lib/format/dates.ts";

describe("Formatting Utilities Suite", () => {
  test("formatCoordinate formats latitude and longitude to standard decimal notation", () => {
    const formatted = formatCoordinate(22.47072, 70.05771);
    assert.equal(formatted, "22.4707° N, 70.0577° E");
  });

  test("formatCoordinate formats southern and western coordinates", () => {
    const formatted = formatCoordinate(-33.8688, -151.2093);
    assert.equal(formatted, "33.8688° S, 151.2093° W");
  });

  test("formatFrp formats MW and GW values correctly", () => {
    assert.equal(formatFrp(45.2), "45.2 MW");
    assert.equal(formatFrp(1250.0), "1.25 GW");
  });

  test("formatPercent formats decimal values as percentage string", () => {
    assert.equal(formatPercent(0.964, 1), "96.4%");
    assert.equal(formatPercent(0.85, 0), "85%");
  });

  test("formatCompactCount formats large numerical counts", () => {
    assert.equal(formatCompactCount(1250), "1.3K");
    assert.equal(formatCompactCount(42), "42");
  });

  test("formatUtcTime returns standard UTC time string", () => {
    const timestamp = new Date("2026-08-31T12:00:00Z");
    assert.equal(formatUtcTime(timestamp), "12:00:00 UTC");
  });

  test("formatUtcDateTime returns date and time in UTC", () => {
    const timestamp = new Date("2026-08-31T12:00:00Z");
    assert.equal(formatUtcDateTime(timestamp), "2026-08-31 · 12:00:00 UTC");
  });

  test("formatRelativeSecondsAgo formats elapsed time", () => {
    assert.equal(formatRelativeSecondsAgo(45), "45s ago");
    assert.equal(formatRelativeSecondsAgo(120), "2m ago");
    assert.equal(formatRelativeSecondsAgo(7200), "2h ago");
  });
});
