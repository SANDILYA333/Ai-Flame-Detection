import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateHaversineDistance,
  formatDistance,
  calculateExposureLevel,
} from "../lib/geo/distance.ts";
import { resolveIndustrialAssets } from "../lib/assets/resolver.ts";
import type { ThermalEvent, EventEvidenceResponse } from "../types/event.ts";

describe("Industrial Asset Intelligence & Geodesic Distance Suite", () => {
  it("calculates accurate geodesic Haversine distance", () => {
    // Distance between Jamnagar centroid and a point ~320m away
    const lat1 = 22.4707;
    const lon1 = 70.0577;
    const lat2 = 22.4735;
    const lon2 = 70.0577;

    const dist = calculateHaversineDistance(lat1, lon1, lat2, lon2);
    assert.ok(dist >= 300 && dist <= 330, `Expected ~311m, got ${dist}m`);

    // Zero distance for identical points
    assert.equal(calculateHaversineDistance(lat1, lon1, lat1, lon1), 0);
  });

  it("formats distances cleanly in meters and kilometers", () => {
    assert.equal(formatDistance(320), "320 m");
    assert.equal(formatDistance(710), "710 m");
    assert.equal(formatDistance(1200), "1.2 km");
    assert.equal(formatDistance(15400), "15 km");
    assert.equal(formatDistance(null), "N/A");
    assert.equal(formatDistance(undefined), "N/A");
  });

  it("assigns exposure levels accurately based on proximity boundaries", () => {
    assert.equal(calculateExposureLevel(200), "HIGH");
    assert.equal(calculateExposureLevel(500), "HIGH");
    assert.equal(calculateExposureLevel(501), "MEDIUM");
    assert.equal(calculateExposureLevel(2000), "MEDIUM");
    assert.equal(calculateExposureLevel(2001), "LOW");
    assert.equal(calculateExposureLevel(null), "NONE");
  });

  it("resolves industrial assets from direct backend context evidence payload", () => {
    const event: ThermalEvent = {
      event_id: "EVT-ASSET-01",
      latitude: 22.4707,
      longitude: 70.0577,
      phenomenon: "FLARE",
      classification: "INDUSTRIAL",
      confidence: 0.96,
      uncertainty_state: "CONFIDENT",
      frp_mw: 245.0,
      detection_count: 10,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T14:00:00Z",
    };

    const evidence: EventEvidenceResponse = {
      event_id: "EVT-ASSET-01",
      context_evidence: [
        {
          evidence_id: "CE-01",
          facility_name: "Reliance Jamnagar Refinery",
          infrastructure_type: "refinery",
          distance_meters: 320,
          source_type: "osm_industrial_poly",
        },
        {
          evidence_id: "CE-02",
          facility_name: "Crude Storage Terminal 4",
          infrastructure_type: "storage_tank",
          distance_meters: 710,
          source_type: "osm_infrastructure",
        },
      ],
      reference_evidence: [],
    };

    const result = resolveIndustrialAssets(event, evidence);

    assert.equal(result.hasAssetData, true);
    assert.equal(result.assets.length, 2);
    assert.equal(result.overallExposure, "HIGH");

    const a1 = result.assets[0];
    assert.equal(a1.name, "Reliance Jamnagar Refinery");
    assert.equal(a1.type, "REFINERY");
    assert.equal(a1.formattedDistance, "320 m");
    assert.equal(a1.exposureLevel, "HIGH");

    const a2 = result.assets[1];
    assert.equal(a2.name, "Crude Storage Terminal 4");
    assert.equal(a2.type, "STORAGE_FACILITY");
    assert.equal(a2.formattedDistance, "710 m");
    assert.equal(a2.exposureLevel, "MEDIUM");
  });

  it("handles events with no proximate assets gracefully without inventing records", () => {
    const openBurnEvent: ThermalEvent = {
      event_id: "EVT-OPEN-01",
      latitude: 31.5,
      longitude: 75.2,
      phenomenon: "OPEN_BURNING",
      classification: "NON_INDUSTRIAL",
      confidence: 0.88,
      uncertainty_state: "CONFIDENT",
      frp_mw: 25.0,
      detection_count: 1,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T13:00:00Z",
      context_summary: "Post-harvest cropland burning in agricultural terrain",
    };

    const result = resolveIndustrialAssets(openBurnEvent, null);

    assert.equal(result.hasAssetData, false);
    assert.equal(result.assets.length, 0);
    assert.equal(result.overallExposure, "NO_ASSETS_DETECTED");
    assert.ok(result.summary.includes("No proximate"));
  });

  it("preserves UNKNOWN classification without mutating state", () => {
    const unknownEvent: ThermalEvent = {
      event_id: "EVT-UNK-01",
      latitude: 25.0,
      longitude: 80.0,
      phenomenon: "UNKNOWN",
      classification: "UNKNOWN",
      confidence: 0.45,
      uncertainty_state: "REVIEW_REQUIRED",
      frp_mw: 80.0,
      detection_count: 1,
      start_time: "2026-08-31T12:00:00Z",
      end_time: "2026-08-31T12:30:00Z",
    };

    const result = resolveIndustrialAssets(unknownEvent, null);

    assert.equal(unknownEvent.classification, "UNKNOWN", "Classification must not be mutated");
    assert.equal(result.hasAssetData, false);
  });

  it("handles malformed and NaN coordinate values without throwing exceptions", () => {
    assert.equal(calculateHaversineDistance(NaN, NaN, 20.0, 70.0), 0);
    assert.equal(calculateHaversineDistance(20.0, 70.0, (undefined as unknown) as number, 70.0), 0);
  });
});
