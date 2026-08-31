import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { generateXaiExplanation, DECISION_THRESHOLD } from "../lib/xai/explainer.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Explainable AI (XAI) Intelligence Suite", () => {
  it("generates grounded explanation for industrial thermal event", () => {
    const industrialEvent: ThermalEvent = {
      event_id: "EVT-TEST-IND-01",
      latitude: 22.45,
      longitude: 70.04,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.964,
      uncertainty_state: "CONFIDENT",
      frp_mw: 245.8,
      detection_count: 3,
      is_persistent: true,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T14:00:00Z",
      location_name: "Jamnagar Petrochemical Complex",
      context_summary: "Active oil & gas refinery flare stack cluster",
    };

    const xai = generateXaiExplanation(industrialEvent);

    assert.equal(xai.assignedClass, "INDUSTRIAL");
    assert.equal(xai.isAbstained, false);
    assert.equal(xai.confidence, 0.964);
    assert.ok(xai.decisionSummary.includes("INDUSTRIAL"));
    assert.ok(xai.signals.length >= 4);

    // Signals check
    const infraSignal = xai.signals.find((s) => s.id === "signal_infrastructure");
    assert.ok(infraSignal);
    assert.equal(infraSignal?.status, "positive");
    assert.equal(infraSignal?.impact, "supports_industrial");

    const frpSignal = xai.signals.find((s) => s.id === "signal_frp");
    assert.ok(frpSignal);
    assert.equal(frpSignal?.status, "positive");

    // Calibrated probability distribution
    const indProb = xai.probabilities.find((p) => p.className === "INDUSTRIAL");
    assert.ok(indProb);
    assert.equal(indProb?.percentage, 96);
  });

  it("generates grounded explanation for non-industrial agricultural event", () => {
    const nonIndEvent: ThermalEvent = {
      event_id: "EVT-TEST-NONIND-01",
      latitude: 31.5,
      longitude: 75.2,
      phenomenon: "OPEN_BURNING",
      classification: "NON_INDUSTRIAL",
      confidence: 0.88,
      uncertainty_state: "CONFIDENT",
      frp_mw: 22.4,
      detection_count: 1,
      is_persistent: false,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T13:00:00Z",
      location_name: "Punjab Agricultural Belt",
      context_summary: "Seasonal crop residue burning in cropland terrain",
    };

    const xai = generateXaiExplanation(nonIndEvent);

    assert.equal(xai.assignedClass, "NON_INDUSTRIAL");
    assert.equal(xai.isAbstained, false);
    assert.ok(xai.decisionSummary.includes("NON_INDUSTRIAL"));

    const nonIndProb = xai.probabilities.find((p) => p.className === "NON_INDUSTRIAL");
    assert.ok(nonIndProb);
    assert.equal(nonIndProb?.percentage, 88);
  });

  it("generates transparent abstention explanation for UNKNOWN / REVIEW_REQUIRED events", () => {
    const unknownEvent: ThermalEvent = {
      event_id: "EVT-TEST-UNK-01",
      latitude: 25.0,
      longitude: 80.0,
      phenomenon: "UNKNOWN",
      classification: "UNKNOWN",
      confidence: 0.45,
      uncertainty_state: "REVIEW_REQUIRED",
      frp_mw: 65.0,
      detection_count: 1,
      is_persistent: false,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T12:30:00Z",
    };

    const xai = generateXaiExplanation(unknownEvent);

    assert.equal(xai.assignedClass, "UNKNOWN");
    assert.equal(xai.isAbstained, true);
    assert.ok(xai.abstentionReason);
    assert.ok(xai.abstentionReason?.includes("threshold"));
    assert.ok(xai.decisionSummary.includes("ABSTAINED"));

    // Quality gate signal must indicate abstention
    const gateSignal = xai.signals.find((s) => s.id === "signal_confidence_gate");
    assert.ok(gateSignal);
    assert.equal(gateSignal?.status, "negative");
    assert.equal(gateSignal?.impact, "indeterminate");
  });

  it("handles null and undefined evidence/intelligence payloads gracefully", () => {
    const event = DEMO_THERMAL_EVENTS[0];
    const xai = generateXaiExplanation(event, null, null);

    assert.ok(xai);
    assert.equal(xai.eventId, event.event_id);
    assert.ok(xai.probabilities.length === 3);
    assert.ok(xai.signals.length >= 4);
    assert.equal(xai.provenance.decisionThreshold, DECISION_THRESHOLD);
  });

  it("generates deterministic XAI outputs across repeated invocations", () => {
    const events = DEMO_THERMAL_EVENTS;

    events.forEach((evt) => {
      const exp1 = generateXaiExplanation(evt);
      const exp2 = generateXaiExplanation(evt);

      assert.equal(exp1.assignedClass, exp2.assignedClass);
      assert.equal(exp1.isAbstained, exp2.isAbstained);
      assert.equal(exp1.decisionSummary, exp2.decisionSummary);
      assert.equal(exp1.signals.length, exp2.signals.length);
      assert.equal(exp1.probabilities.length, exp2.probabilities.length);
    });
  });
});
