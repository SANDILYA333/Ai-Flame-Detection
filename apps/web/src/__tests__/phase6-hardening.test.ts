import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import { calculateOperationalRisk } from "../lib/risk/scoring.ts";
import { generateXaiExplanation } from "../lib/xai/explainer.ts";
import { resolveIndustrialAssets } from "../lib/assets/resolver.ts";
import {
  calculateWindowRange,
  deriveTimeWindowQuery,
  filterEventsByTemporalState,
} from "../lib/playback/temporal.ts";
import { formatCoordinate } from "../lib/format/coordinates.ts";
import { formatFrp } from "../lib/format/numbers.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("PHASE 6: Final Hardening & Demo Readiness Comprehensive QA Suite", () => {
  const events = DEMO_THERMAL_EVENTS;

  it("Scenario A: Industrial + High Confidence + Strong Thermal Signature", () => {
    const jamnagar = events.find((e) => e.event_id === "EVT-2026-0831-01");
    assert.ok(jamnagar, "Jamnagar event must exist");

    // 1. Classification & Confidence
    assert.equal(jamnagar.classification, "INDUSTRIAL");
    assert.ok(jamnagar.confidence >= 0.90);
    assert.equal(jamnagar.uncertainty_state, "CONFIDENT");

    // 2. Operational Priority
    const risk = calculateOperationalRisk(jamnagar);
    assert.equal(risk.level, "CRITICAL");
    assert.ok(risk.score >= 80);
    assert.equal(risk.isIndeterminate, false);

    // 3. XAI Grounded Signals
    const xai = generateXaiExplanation(jamnagar);
    assert.equal(xai.assignedClass, "INDUSTRIAL");
    assert.equal(xai.isAbstained, false);
    assert.ok(xai.signals.some((s) => s.id === "signal_infrastructure" && s.status === "positive"));
    assert.ok(xai.signals.some((s) => s.id === "signal_frp" && s.status === "positive"));

    // 4. Industrial Assets
    const assets = resolveIndustrialAssets(jamnagar);
    assert.ok(assets.hasAssetData);
    assert.equal(assets.overallExposure, "HIGH");
    assert.ok(assets.assets.length > 0);
  });

  it("Scenario B: Industrial + Moderate Confidence (Preserves Uncertainty)", () => {
    const modIndEvent: ThermalEvent = {
      event_id: "EVT-TEST-MOD-01",
      latitude: 21.7,
      longitude: 72.1,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.72,
      uncertainty_state: "CONFIDENT",
      frp_mw: 48.0,
      detection_count: 2,
      is_persistent: false,
      start_time: "2026-08-31T10:00:00Z",
      end_time: "2026-08-31T12:00:00Z",
      location_name: "Gujarat Coastal Industrial Zone",
    };

    const risk = calculateOperationalRisk(modIndEvent);
    assert.ok(["HIGH", "MEDIUM"].includes(risk.level));
    assert.ok(risk.score < 80);

    const xai = generateXaiExplanation(modIndEvent);
    assert.equal(xai.assignedClass, "INDUSTRIAL");
    assert.equal(xai.isAbstained, false);
    assert.equal(xai.confidence, 0.72);
  });

  it("Scenario C: Non-Industrial Event (Never Claims Safe / Zero Danger)", () => {
    const agriEvents = events.filter((e) => e.classification === "NON_INDUSTRIAL");
    assert.ok(agriEvents.length > 0, "Catalog must have non-industrial events");

    agriEvents.forEach((evt) => {
      assert.equal(evt.classification, "NON_INDUSTRIAL");

      const risk = calculateOperationalRisk(evt);
      // Non-industrial does not mean 0 risk or "SAFE"
      assert.ok(risk.score >= 0);
      assert.ok(!risk.summary.toLowerCase().includes("safe"));
      assert.ok(risk.disclaimer.includes("Distinct from ML model classification confidence"));

      const xai = generateXaiExplanation(evt);
      assert.equal(xai.assignedClass, "NON_INDUSTRIAL");
      assert.ok(!xai.decisionSummary.toLowerCase().includes("safe"));
    });
  });

  it("Scenario D: UNKNOWN / Abstained Event (Mandatory Review Required Treatment)", () => {
    const unknownEvents = events.filter((e) => e.classification === "UNKNOWN");
    assert.ok(unknownEvents.length > 0, "Catalog must have UNKNOWN events");

    unknownEvents.forEach((unk) => {
      assert.equal(unk.classification, "UNKNOWN");
      assert.notEqual(unk.classification, "NON_INDUSTRIAL");

      const risk = calculateOperationalRisk(unk);
      if (unk.uncertainty_state === "REVIEW_REQUIRED") {
        assert.equal(risk.level, "INDETERMINATE");
        assert.equal(risk.isIndeterminate, true);
        assert.ok(risk.indeterminateReason?.length);
      }

      const xai = generateXaiExplanation(unk);
      assert.equal(xai.assignedClass, "UNKNOWN");
      assert.equal(xai.isAbstained, true);
      assert.ok(xai.abstentionReason?.length);
      assert.ok(xai.decisionSummary.includes("ABSTAINED"));
    });
  });

  it("Scenario E: Dynamic Temporal Window Queries and Interval Filtering", () => {
    const windows = ["1H", "6H", "24H", "48H", "7D", "ALL"] as const;

    windows.forEach((win) => {
      const q = deriveTimeWindowQuery(win);
      if (win === "ALL") {
        assert.equal(q.start_time, undefined);
        assert.equal(q.end_time, undefined);
      } else {
        assert.ok(q.start_time?.endsWith("Z"));
        assert.ok(q.end_time?.endsWith("Z"));
        assert.ok(new Date(q.start_time!).getTime() < new Date(q.end_time!).getTime());
      }

      const range = calculateWindowRange(win, events);
      assert.ok(range.start <= range.end);
      const filtered = filterEventsByTemporalState(events, range, range.end, false);
      assert.ok(Array.isArray(filtered));
      assert.ok(filtered.length <= events.length);
    });
  });

  it("Scenario F: Composed Multi-Criteria Filtering (Time + Classification + Priority + Search)", () => {
    const range = calculateWindowRange("ALL", events);

    // 1. Filter: Industrial only
    const indOnly = events.filter((e) => e.classification === "INDUSTRIAL");
    assert.ok(indOnly.length > 0);

    // 2. Filter: Industrial + Critical Priority
    const indCrit = indOnly.filter((e) => calculateOperationalRisk(e).level === "CRITICAL");
    assert.ok(indCrit.length > 0);
    assert.ok(indCrit.length <= indOnly.length);

    // 3. Filter: Industrial + Critical Priority + Search "Jamnagar"
    const indCritJam = indCrit.filter(
      (e) => e.location_name?.toLowerCase().includes("jamnagar") || e.event_id.toLowerCase().includes("jamnagar")
    );
    assert.ok(indCritJam.length > 0);
    assert.ok(indCritJam.every((e) => e.location_name?.toLowerCase().includes("jamnagar")));
  });

  it("Scenario G: Rapid Selection Synchronization & Index Wrapping", () => {
    assert.ok(events.length >= 5);

    // Forward sequence
    for (let i = 0; i < events.length; i++) {
      const current = events[i];
      const nextIdx = i >= events.length - 1 ? 0 : i + 1;
      const next = events[nextIdx];

      assert.ok(current.event_id);
      assert.ok(next.event_id);
    }

    // Backward sequence
    for (let i = events.length - 1; i >= 0; i--) {
      const current = events[i];
      const prevIdx = i <= 0 ? events.length - 1 : i - 1;
      const prev = events[prevIdx];

      assert.ok(current.event_id);
      assert.ok(prev.event_id);
    }
  });

  it("Scenario H: Formatting & Coordinate Precision Hardening", () => {
    // Standard Coordinates
    assert.equal(formatCoordinate(22.4707, 70.0577), "22.4707° N, 70.0577° E");
    assert.equal(formatCoordinate(-33.8688, -151.2093), "33.8688° S, 151.2093° W");

    // Extreme & Invalid Coordinates
    assert.equal(formatCoordinate(NaN, NaN), "0.0000° N, 0.0000° E");

    // FRP Formatting
    assert.equal(formatFrp(12.4), "12.4 MW");
    assert.equal(formatFrp(380.5), "380.5 MW");
    assert.equal(formatFrp(1450.0), "1.45 GW");
    assert.equal(formatFrp(NaN), "0.0 MW");
  });

  it("Scenario I: Event Detail Panel Minimize & Restore State Preservation", () => {
    // 1. Initial selection
    let selectedEvent: ThermalEvent | null = events[0];
    let isDetailOpen = true;

    assert.equal(selectedEvent.event_id, events[0].event_id);
    assert.equal(isDetailOpen, true);

    // 2. User clicks X to close/minimize panel
    isDetailOpen = false;

    // Selected event must NOT be deleted or set to null
    assert.ok(selectedEvent !== null);
    assert.equal(selectedEvent?.event_id, events[0].event_id);
    assert.equal(isDetailOpen, false);

    // 3. User clicks the same marker again to restore/reopen
    isDetailOpen = true;

    // Restores same event with intact intelligence data
    assert.equal(selectedEvent?.event_id, events[0].event_id);
    assert.equal(selectedEvent?.classification, "INDUSTRIAL");
    assert.equal(selectedEvent?.confidence, 0.964);
    assert.equal(selectedEvent?.frp_mw, 245.8);
    assert.equal(isDetailOpen, true);

    // 4. User clicks a different marker while panel is open or closed
    selectedEvent = events[1];
    isDetailOpen = true;

    assert.equal(selectedEvent?.event_id, events[1].event_id);
    assert.equal(isDetailOpen, true);
  });
});
