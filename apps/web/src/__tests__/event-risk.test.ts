import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { calculateOperationalRisk, getRiskLevelStyles } from "../lib/risk/scoring.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Operational Risk & Severity Intelligence Suite", () => {
  it("calculates deterministic risk assessment for standard industrial event", () => {
    const industrialEvent: ThermalEvent = {
      event_id: "EVT-TEST-IND-01",
      latitude: 22.45,
      longitude: 70.04,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.96,
      uncertainty_state: "CONFIDENT",
      frp_mw: 280.0, // FRP >= 250 -> 40 pts
      detection_count: 6, // >= 5 -> 10 pts
      is_persistent: true, // persistent -> 25 pts
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T14:00:00Z",
    };

    const result = calculateOperationalRisk(industrialEvent);

    // Total: 40 (FRP) + 25 (Persistence) + 25 (Industrial) + 10 (Cluster) = 100
    assert.equal(result.score, 100);
    assert.equal(result.level, "CRITICAL");
    assert.equal(result.isIndeterminate, false);
    assert.equal(result.factors.length, 4);
    assert.ok(result.disclaimer.includes("Distinct from ML model classification confidence"));
  });

  it("calculates low risk for transient minor non-industrial event", () => {
    const lowRiskEvent: ThermalEvent = {
      event_id: "EVT-TEST-LOW-01",
      latitude: 31.5,
      longitude: 75.2,
      phenomenon: "OPEN_BURNING",
      classification: "NON_INDUSTRIAL",
      confidence: 0.85,
      uncertainty_state: "CONFIDENT",
      frp_mw: 10.0, // < 15 -> 5 pts
      detection_count: 1, // 1 -> 2 pts
      is_persistent: false, // transient -> 5 pts
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T12:30:00Z",
    };

    const result = calculateOperationalRisk(lowRiskEvent);

    // Total: 5 (FRP) + 5 (Persistence) + 10 (Non-Industrial) + 2 (Cluster) = 22
    assert.equal(result.score, 22);
    assert.equal(result.level, "LOW");
    assert.equal(result.isIndeterminate, false);
  });

  it("safely handles UNKNOWN and REVIEW_REQUIRED events as INDETERMINATE", () => {
    const unknownEvent: ThermalEvent = {
      event_id: "EVT-TEST-UNK-01",
      latitude: 25.0,
      longitude: 80.0,
      phenomenon: "UNKNOWN",
      classification: "UNKNOWN",
      confidence: 0.45,
      uncertainty_state: "REVIEW_REQUIRED",
      frp_mw: 150.0,
      detection_count: 2,
      is_persistent: false,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T12:30:00Z",
    };

    const result = calculateOperationalRisk(unknownEvent);

    assert.equal(result.level, "INDETERMINATE");
    assert.equal(result.isIndeterminate, true);
    assert.ok(result.indeterminateReason?.includes("Awaiting"));
    assert.notEqual(result.level, "LOW", "Unknown event must never silently be assigned LOW risk");
  });

  it("handles missing and NaN fields gracefully without runtime exceptions", () => {
    const malformedEvent: ThermalEvent = {
      event_id: "EVT-TEST-NAN-01",
      latitude: 0,
      longitude: 0,
      phenomenon: "UNKNOWN",
      classification: "NON_INDUSTRIAL",
      confidence: 0,
      uncertainty_state: "CONFIDENT",
      frp_mw: NaN,
      detection_count: (undefined as unknown) as number,
      start_time: "invalid-date",
      end_time: "invalid-date",
    };

    const result = calculateOperationalRisk(malformedEvent);

    assert.ok(result.score >= 0 && result.score <= 100);
    assert.ok(["LOW", "MEDIUM", "HIGH", "CRITICAL", "INDETERMINATE"].includes(result.level));
  });

  it("evaluates all catalog events deterministically", () => {
    const events: ThermalEvent[] = DEMO_THERMAL_EVENTS;

    events.forEach((evt) => {
      const assessment1 = calculateOperationalRisk(evt);
      const assessment2 = calculateOperationalRisk(evt);

      assert.equal(assessment1.score, assessment2.score);
      assert.equal(assessment1.level, assessment2.level);
      assert.equal(assessment1.isIndeterminate, assessment2.isIndeterminate);

      const styles = getRiskLevelStyles(assessment1.level);
      assert.ok(styles.bg);
      assert.ok(styles.text);
      assert.ok(styles.border);
      assert.ok(styles.label);
    });
  });
});
