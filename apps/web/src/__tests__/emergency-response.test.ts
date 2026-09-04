import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateLocalResponseRecommendation,
  LOCAL_EMERGENCY_RESPONDERS,
} from "../lib/responders/engine.ts";
import {
  postNotifyResponder,
  fetchResponseActivity,
} from "../lib/responders/api.ts";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import type { ThermalEvent } from "../types/event.ts";

describe("Emergency Response & Analyst-Confirmed Notification Suite", () => {
  it("verifies embedded emergency responders dataset contains valid metadata and coordinates", () => {
    assert.ok(LOCAL_EMERGENCY_RESPONDERS.length >= 8);

    LOCAL_EMERGENCY_RESPONDERS.forEach((r) => {
      assert.ok(r.id, "Responder must have an ID");
      assert.ok(r.name, "Responder must have a name");
      assert.ok(r.city, "Responder must have a city");
      assert.ok(r.phone, "Responder must have a phone number");
      assert.ok(r.capabilities.length > 0, "Responder must have capabilities");
      assert.ok(r.lat >= -90 && r.lat <= 90, "Latitude must be valid WGS-84");
      assert.ok(r.lon >= -180 && r.lon <= 180, "Longitude must be valid WGS-84");
    });
  });

  it("calculates CRITICAL operational priority for high-intensity industrial event (>50 MW FRP)", () => {
    const industrialHighFrp: ThermalEvent = {
      event_id: "EVT-CRITICAL-TEST",
      latitude: 22.4707,
      longitude: 70.0577,
      phenomenon: "fire",
      classification: "INDUSTRIAL",
      confidence: 0.98,
      uncertainty_state: "CONFIDENT",
      frp_mw: 120.0,
      detection_count: 8,
      start_time: "2026-08-31T06:00:00Z",
      end_time: "2026-08-31T06:30:00Z",
      is_persistent: false,
      location_name: "Jamnagar Petrochemical Complex",
      context_summary: "Major heavy industrial refining unit with high thermal radiation",
    };

    const rec = calculateLocalResponseRecommendation(industrialHighFrp);
    assert.equal(rec.event_id, "EVT-CRITICAL-TEST");
    assert.equal(rec.response_priority, "CRITICAL");
    assert.equal(rec.is_routine_flare, false);
    assert.equal(rec.is_abstained_or_unknown, false);
    assert.equal(rec.escalation_type, "CRITICAL_MEDICAL");
    assert.equal(rec.auto_escalation_eligible, true);
    assert.ok(rec.priority_reason.includes("High-intensity"));
    assert.ok(rec.responders.length > 0);

    // Nearest responder should be Jamnagar Fire Station (~0 km)
    const topResp = rec.responders[0];
    assert.equal(topResp.id, "fire-002");
    assert.ok(topResp.distance_meters < 2000, "Should be within 2km");
    assert.ok((topResp.estimated_eta_minutes ?? 0) <= 5, "ETA should be minimal");
  });

  it("extracts nearest 2 hospitals and nearest 2 fire stations correctly", () => {
    const sampleEvent = DEMO_THERMAL_EVENTS[0];
    const rec = calculateLocalResponseRecommendation(sampleEvent);

    assert.ok(rec.nearest_hospitals);
    assert.ok(rec.nearest_fire_stations);
    assert.equal(rec.nearest_hospitals.length, 2);
    assert.equal(rec.nearest_fire_stations.length, 2);

    rec.nearest_hospitals.forEach((h) => {
      assert.ok(h.type === "BURN_ICU" || h.type === "HOSPITAL");
    });
    rec.nearest_fire_stations.forEach((f) => {
      assert.ok(f.type === "CHEMICAL_FIRE_STATION" || f.type === "FIRE_STATION");
    });
  });

  it("evaluates confidence escalation thresholds properly", () => {
    const highConfAutoEvent: ThermalEvent = {
      ...DEMO_THERMAL_EVENTS[0],
      event_id: "EVT-HIGH-AUTO",
      frp_mw: 20.0,
      confidence: 0.992,
    };
    const recAuto = calculateLocalResponseRecommendation(highConfAutoEvent);
    assert.equal(recAuto.escalation_type, "HIGH_CONFIDENCE_AUTO");
    assert.equal(recAuto.auto_escalation_eligible, true);

    const highConfReviewEvent: ThermalEvent = {
      ...DEMO_THERMAL_EVENTS[0],
      event_id: "EVT-HIGH-REVIEW",
      frp_mw: 20.0,
      confidence: 0.965,
    };
    const recReview = calculateLocalResponseRecommendation(highConfReviewEvent);
    assert.equal(recReview.escalation_type, "ADMIN_CONFIRMED");
    assert.equal(recReview.auto_escalation_eligible, false);
  });

  it("calculates MONITOR_ONLY for routine operational flaring to prevent false alarms", () => {
    const routineFlare: ThermalEvent = {
      event_id: "EVT-FLARE-ROUTINE",
      latitude: 22.4707,
      longitude: 70.0577,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.95,
      uncertainty_state: "CONFIDENT",
      frp_mw: 32.0,
      detection_count: 15,
      start_time: "2026-08-31T01:00:00Z",
      end_time: "2026-08-31T06:00:00Z",
      is_persistent: true,
      source_id: "SRC-FLARE-001",
      location_name: "Refinery Flare Stack North",
      context_summary: "Routine flaring stack operations at industrial facility",
    };

    const rec = calculateLocalResponseRecommendation(routineFlare);
    assert.equal(rec.response_priority, "MONITOR_ONLY");
    assert.equal(rec.is_routine_flare, true);
    assert.ok(rec.priority_reason.includes("Routine operational flaring"));
  });

  it("calculates REVIEW_REQUIRED for UNKNOWN / abstained events", () => {
    const unknownEvent: ThermalEvent = {
      event_id: "EVT-UNKNOWN-TEST",
      latitude: 20.5,
      longitude: 78.5,
      phenomenon: "UNKNOWN",
      classification: "UNKNOWN",
      confidence: 0.42,
      uncertainty_state: "REVIEW_REQUIRED",
      frp_mw: 18.0,
      detection_count: 2,
      start_time: "2026-08-31T04:00:00Z",
      end_time: "2026-08-31T04:15:00Z",
      is_persistent: false,
      location_name: "Unclassified Spatial Anomaly",
      context_summary: "Sparse detection cluster with conflicting contextual features",
    };

    const rec = calculateLocalResponseRecommendation(unknownEvent);
    assert.equal(rec.response_priority, "REVIEW_REQUIRED");
    assert.equal(rec.is_abstained_or_unknown, true);
    assert.ok(rec.priority_reason.includes("Analyst review required"));
  });

  it("ranks responders with Fire Services first, then Medical, then NDRF", () => {
    const sampleEvent = DEMO_THERMAL_EVENTS[0];
    const rec = calculateLocalResponseRecommendation(sampleEvent);

    assert.ok(rec.responders.length >= 3);
    const types = rec.responders.map((r) => r.type);

    // Fire station should be ranked first
    assert.ok(
      types[0] === "CHEMICAL_FIRE_STATION" || types[0] === "FIRE_STATION",
      "First responder should be Fire Services"
    );

    // Medical should be ranked before NDRF
    const firstMedIdx = types.findIndex((t) => t === "BURN_ICU" || t === "HOSPITAL");
    const ndrfIdx = types.findIndex((t) => t === "NDRF");

    assert.ok(firstMedIdx >= 0, "Medical responder must be present");
    assert.ok(ndrfIdx >= 0, "NDRF responder must be present");
    assert.ok(firstMedIdx < ndrfIdx, "Medical should precede NDRF");
  });

  it("simulates multi-channel notification and updates response activity history", async () => {
    const eventId = DEMO_THERMAL_EVENTS[0].event_id;
    const responder = LOCAL_EMERGENCY_RESPONDERS[0];

    const result = await postNotifyResponder(
      eventId,
      {
        responder_id: responder.id,
        action: "NOTIFY",
        mode: "SIMULATED",
        recipient_phone: "+91 9876543210",
        channels: ["SMS", "WHATSAPP"],
        escalation_type: "ADMIN_CONFIRMED",
        analyst_notes: "Priority dispatch multi-channel test",
      },
      responder.name,
      responder.type
    );

    assert.equal(result.status, "SIMULATED");
    assert.equal(result.mode, "SIMULATED");
    assert.equal(result.responder_id, responder.id);
    assert.equal(result.recipient_phone, "+91 9876543210");
    assert.ok(result.channels);
    assert.equal(result.channels.length, 2);
    assert.ok(result.notification_id.startsWith(`NOTIF-${eventId}`));

    // Fetch activity
    const activity = await fetchResponseActivity(eventId);
    assert.ok(activity.length >= 1);
    assert.equal(activity[0].responder_id, responder.id);
    assert.equal(activity[0].status, "SIMULATED");
    assert.equal(activity[0].recipient_phone, "+91 9876543210");
    assert.equal(activity[0].analyst_notes, "Priority dispatch multi-channel test");
  });
});
