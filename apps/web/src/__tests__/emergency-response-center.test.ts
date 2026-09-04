import { describe, it } from "node:test";
import assert from "node:assert/strict";
import type { ThermalEvent } from "../types/event.ts";
import type {
  EventResponseRecommendation,
  EmergencyResponder,
  ResponseActivityRecord,
  NotificationRequest,
} from "../types/responders.ts";
import {
  fetchEventResponders,
  postNotifyResponder,
  fetchResponseActivity,
} from "../lib/responders/api.ts";

describe("Emergency Response Center & Operator Interaction Suite (Phase 4)", () => {
  const mockIndustrialEvent: ThermalEvent = {
    event_id: "evt_test_jamnagar_001",
    detection_count: 8,
    latitude: 22.4707,
    longitude: 70.0577,
    frp_mw: 85.5,
    phenomenon: "industrial_thermal_source",
    classification: "INDUSTRIAL",
    confidence: 0.965,
    uncertainty_state: "CONFIDENT",
    start_time: "2026-08-31T08:00:00Z",
    end_time: "2026-08-31T08:45:00Z",
    is_persistent: true,
    location_name: "Jamnagar Petrochemical Complex",
    context_summary: "Major crude distillation and refinery unit",
  };

  it("Step 1: Fetches authoritative responder data with correct event ID", async () => {
    const rec = await fetchEventResponders(mockIndustrialEvent, "+91 9876543210");
    assert.ok(rec, "Should return recommendation");
    assert.equal(rec.event_id, mockIndustrialEvent.event_id);
    assert.ok(rec.response_priority, "Priority must exist");
    assert.ok(Array.isArray(rec.responders), "Responders array must exist");
  });

  it("Step 2: Correctly extracts top 2 fire stations and top 2 hospitals without fabricating", async () => {
    const rec = await fetchEventResponders(mockIndustrialEvent);
    assert.ok(rec.nearest_fire_stations, "Fire stations should be present");
    assert.ok(rec.nearest_fire_stations.length <= 2, "Max 2 fire stations");
    assert.ok(rec.nearest_hospitals, "Hospitals should be present");
    assert.ok(rec.nearest_hospitals.length <= 2, "Max 2 hospitals");

    // Distances must be non-negative
    rec.nearest_fire_stations.forEach((fs) => {
      assert.ok(fs.distance_meters >= 0);
      assert.ok(fs.name.length > 0);
    });
    rec.nearest_hospitals.forEach((h) => {
      assert.ok(h.distance_meters >= 0);
      assert.ok(h.name.length > 0);
    });
  });

  it("Step 3: Preserves event selection context during notification simulation", async () => {
    const request: NotificationRequest = {
      responder_id: "fire-002",
      action: "NOTIFY",
      mode: "SIMULATED",
      recipient_phone: "+91 9876543210",
      channels: ["SMS", "WHATSAPP"],
      escalation_type: "ADMIN_CONFIRMED",
      analyst_notes: "Phase 4 verification test",
    };

    const response = await postNotifyResponder(
      mockIndustrialEvent.event_id,
      request,
      "Jamnagar Industrial Fire Brigade HQ",
      "CHEMICAL_FIRE_STATION"
    );

    assert.ok(response, "Notification response should be returned");
    assert.equal(response.event_id, mockIndustrialEvent.event_id);
    assert.equal(response.responder_id, "fire-002");
    assert.ok(response.message.includes("successfully") || response.status === "SIMULATED");

    // Verify activity history is updated
    const activity = await fetchResponseActivity(mockIndustrialEvent.event_id);
    assert.ok(activity.length > 0, "Activity record must be present");
    const lastRecord = activity[0];
    assert.equal(lastRecord.event_id, mockIndustrialEvent.event_id);
    assert.equal(lastRecord.responder_id, "fire-002");
  });

  it("Step 4: Supports event switching cleanly without leaking stale responder state", async () => {
    const eventA = mockIndustrialEvent;
    const eventB: ThermalEvent = {
      event_id: "evt_test_singrauli_002",
      detection_count: 5,
      latitude: 24.1997,
      longitude: 82.6645,
      frp_mw: 42.0,
      phenomenon: "industrial_thermal_source",
      classification: "INDUSTRIAL",
      confidence: 0.92,
      uncertainty_state: "CONFIDENT",
      start_time: "2026-08-31T09:00:00Z",
      end_time: "2026-08-31T09:30:00Z",
      is_persistent: false,
      location_name: "Singrauli Thermal Power Station",
    };

    const recA = await fetchEventResponders(eventA);
    const recB = await fetchEventResponders(eventB);

    assert.notEqual(recA.event_id, recB.event_id);
    assert.equal(recA.event_id, "evt_test_jamnagar_001");
    assert.equal(recB.event_id, "evt_test_singrauli_002");

    // Responders should be geospatially distinct
    const topRespA = recA.responders[0];
    const topRespB = recB.responders[0];
    assert.notEqual(topRespA.id, topRespB.id, "Different geographic origins must match different responders");
  });

  it("Step 5: Handles simulated demo mode truthfully without claiming real world dispatch", async () => {
    const request: NotificationRequest = {
      responder_id: "hosp-002",
      action: "NOTIFY",
      mode: "SIMULATED",
      recipient_phone: "+91 9876543210",
      channels: ["SMS", "WHATSAPP"],
      escalation_type: "CRITICAL_MEDICAL",
    };

    const res = await postNotifyResponder(
      mockIndustrialEvent.event_id,
      request,
      "GG Government Hospital & Toxic Trauma ICU",
      "BURN_ICU"
    );

    assert.ok(res.mode === "SIMULATED" || res.status === "SIMULATED");
  });
});
