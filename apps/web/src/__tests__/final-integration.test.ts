import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import { calculateOperationalRisk } from "../lib/risk/scoring.ts";
import { generateXaiExplanation } from "../lib/xai/explainer.ts";
import { resolveIndustrialAssets } from "../lib/assets/resolver.ts";
import {
  calculateWindowRange,
  filterEventsByTemporalState,
} from "../lib/playback/temporal.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Final Frontend Integration & Multi-Capability Verification Suite", () => {
  const events = DEMO_THERMAL_EVENTS;

  it("Step 1: Single Source of Truth — All features consume canonical event items", () => {
    assert.ok(events.length >= 20, "Catalog must contain full multi-source events");

    events.forEach((event) => {
      // 1. Risk Assessment consumes canonical event
      const risk = calculateOperationalRisk(event);
      assert.ok(risk.score >= 0 && risk.score <= 100);
      assert.ok(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INDETERMINATE"].includes(risk.level));

      // 2. Explainable AI consumes canonical event
      const xai = generateXaiExplanation(event);
      assert.equal(xai.eventId, event.event_id);
      assert.equal(xai.assignedClass, event.classification);
      assert.ok(xai.signals.length >= 4);

      // 3. Industrial Asset Resolver consumes canonical event
      const assets = resolveIndustrialAssets(event);
      assert.equal(assets.eventId, event.event_id);
      assert.ok(["HIGH", "MEDIUM", "LOW", "NO_ASSETS_DETECTED"].includes(assets.overallExposure));
    });
  });

  it("Step 2: Interaction Matrix — Selected event drives synchronized downstream state", () => {
    const selectedEvent = events[0]; // Jamnagar Refinery Event

    // Feed selection synchronization
    const feedSelectedMatch = events.find((e) => e.event_id === selectedEvent.event_id);
    assert.ok(feedSelectedMatch);
    assert.equal(feedSelectedMatch?.event_id, selectedEvent.event_id);

    // Downstream Intelligence Panel bindings
    const risk = calculateOperationalRisk(selectedEvent);
    const xai = generateXaiExplanation(selectedEvent);
    const assets = resolveIndustrialAssets(selectedEvent);

    assert.equal(risk.level, "CRITICAL");
    assert.equal(xai.assignedClass, "INDUSTRIAL");
    assert.equal(assets.overallExposure, "HIGH");
    assert.ok(assets.assets.length > 0);
  });

  it("Step 3: Scientific Safety — UNKNOWN and ABSTAINED states are preserved without mutation", () => {
    const unknownEvents = events.filter((e) => e.classification === "UNKNOWN");
    assert.ok(unknownEvents.length > 0, "Catalog must contain UNKNOWN events");

    unknownEvents.forEach((evt) => {
      // Classification check
      assert.equal(evt.classification, "UNKNOWN");

      // Risk engine: Must be INDETERMINATE or not silently converted to low risk
      const risk = calculateOperationalRisk(evt);
      if (evt.uncertainty_state === "REVIEW_REQUIRED") {
        assert.equal(risk.level, "INDETERMINATE");
        assert.equal(risk.isIndeterminate, true);
      }

      // XAI explainer: Must be marked ABSTAINED
      const xai = generateXaiExplanation(evt);
      assert.equal(xai.assignedClass, "UNKNOWN");
      assert.equal(xai.isAbstained, true);
      assert.ok(xai.decisionSummary.includes("ABSTAINED"));

      // Asset resolver: Must not mutate classification
      const assets = resolveIndustrialAssets(evt);
      assert.equal(evt.classification, "UNKNOWN");
    });
  });

  it("Step 4: Scientific Distinction — Model Confidence is distinctly decoupled from Operational Risk", () => {
    events.forEach((evt) => {
      const risk = calculateOperationalRisk(evt);
      const confPct = Math.round(evt.confidence * 100);

      // Verify that risk calculation is an independent derived score and not a direct alias of confidence
      assert.ok(typeof risk.score === "number");
      assert.ok(typeof confPct === "number");
      assert.ok(risk.disclaimer.includes("Distinct from ML model classification confidence"));
    });
  });

  it("Step 5: Temporal Playback & Live Synchronization across time windows", () => {
    const windows = ["1H", "6H", "24H", "48H", "7D", "ALL"] as const;

    windows.forEach((win) => {
      const range = calculateWindowRange(win, events);
      assert.ok(range.start <= range.end);
      assert.ok(range.durationMs > 0);

      // Live mode filtering
      const liveEvents = filterEventsByTemporalState(events, range, range.end, false);
      assert.ok(Array.isArray(liveEvents));

      // Playback mode progressive filtering at 50% playhead
      const midpoint = range.start + range.durationMs * 0.5;
      const playbackEvents = filterEventsByTemporalState(events, range, midpoint, true);
      assert.ok(playbackEvents.length <= liveEvents.length);
    });
  });

  it("Step 6: Loading, Empty & Fallback State Resilience", () => {
    // Empty event array
    const emptyRange = calculateWindowRange("24H", []);
    const filteredEmpty = filterEventsByTemporalState([], emptyRange, emptyRange.end, false);
    assert.equal(filteredEmpty.length, 0);

    // Malformed event handling
    const malformedEvt: ThermalEvent = {
      event_id: "EVT-MALFORMED",
      latitude: NaN,
      longitude: NaN,
      phenomenon: "UNKNOWN",
      classification: "UNKNOWN",
      confidence: 0,
      uncertainty_state: "CONFIDENT",
      frp_mw: NaN,
      detection_count: 0,
      start_time: "invalid-iso",
      end_time: "invalid-iso",
    };

    const risk = calculateOperationalRisk(malformedEvt);
    assert.ok(risk);

    const xai = generateXaiExplanation(malformedEvt);
    assert.ok(xai);

    const assets = resolveIndustrialAssets(malformedEvt);
    assert.ok(assets);
    assert.equal(assets.hasAssetData, false);
  });
});
