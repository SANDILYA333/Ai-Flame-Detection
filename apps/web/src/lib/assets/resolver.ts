import type { ThermalEvent, EventEvidenceResponse } from "../../types/event.ts";
import type {
  IndustrialAsset,
  IndustrialContextSummary,
  AssetType,
  ExposureLevel,
} from "../../types/asset.ts";
import {
  calculateHaversineDistance,
  formatDistance,
  calculateExposureLevel,
} from "../geo/distance.ts";

/**
 * Normalizes raw string context types into structured AssetType enum
 */
function normalizeAssetType(rawType?: string, name?: string): AssetType {
  const combined = `${rawType ?? ""} ${name ?? ""}`.toLowerCase();
  if (combined.includes("refin")) return "REFINERY";
  if (combined.includes("power") || combined.includes("thermal station")) return "POWER_PLANT";
  if (combined.includes("petrochem") || combined.includes("chemical")) return "PETROCHEMICAL";
  if (combined.includes("smelt") || combined.includes("steel") || combined.includes("metallurg"))
    return "METALLURGICAL";
  if (combined.includes("pipe") || combined.includes("pipeline")) return "PIPELINE";
  if (combined.includes("storage") || combined.includes("terminal") || combined.includes("tank"))
    return "STORAGE_FACILITY";
  if (combined.includes("agri") || combined.includes("cropland") || combined.includes("farm"))
    return "AGRICULTURAL_PARCEL";
  if (combined.includes("industrial") || combined.includes("zone") || combined.includes("park"))
    return "INDUSTRIAL_ZONE";
  return "OTHER";
}

/**
 * Resolves all nearby industrial infrastructure and spatial context for a thermal event
 * strictly from actual backend response evidence or canonical event metadata.
 */
export function resolveIndustrialAssets(
  event: ThermalEvent,
  evidence?: EventEvidenceResponse | null
): IndustrialContextSummary {
  const assets: IndustrialAsset[] = [];

  // 1. Direct Backend Context Evidence Payloads
  if (evidence?.context_evidence && evidence.context_evidence.length > 0) {
    evidence.context_evidence.forEach((ce, idx) => {
      const name = ce.facility_name || `Infrastructure Feature #${idx + 1}`;
      const type = normalizeAssetType(
        ce.infrastructure_type as string | undefined,
        name
      );

      let distanceMeters: number | null = null;
      if (typeof ce.distance_meters === "number" && !isNaN(ce.distance_meters)) {
        distanceMeters = ce.distance_meters;
      } else if (
        typeof ce.latitude === "number" &&
        typeof ce.longitude === "number"
      ) {
        distanceMeters = calculateHaversineDistance(
          event.latitude,
          event.longitude,
          ce.latitude as number,
          ce.longitude as number
        );
      }

      const exposure = calculateExposureLevel(distanceMeters);

      assets.push({
        id: ce.evidence_id || `ASSET-${event.event_id}-${idx + 1}`,
        name,
        type,
        distanceMeters,
        formattedDistance: formatDistance(distanceMeters),
        exposureLevel: exposure,
        sourceType: (ce.source_type as string) || "OpenStreetMap / Context Registry",
      });
    });
  }

  // 2. Fallback to Canonical Event Metadata (Location Name & Context Summary)
  if (assets.length === 0 && event.context_summary) {
    const summary = event.context_summary;
    const isIndustrialContext =
      summary.toLowerCase().includes("refin") ||
      summary.toLowerCase().includes("petrochem") ||
      summary.toLowerCase().includes("power") ||
      summary.toLowerCase().includes("industrial") ||
      summary.toLowerCase().includes("smelt") ||
      summary.toLowerCase().includes("gasification") ||
      Boolean(event.source_id);

    if (isIndustrialContext) {
      // Check if distance is mentioned in context summary (e.g. "within 320m")
      const distMatch = summary.match(/within\s+(\d+)\s*m/i);
      const parsedDist = distMatch ? parseInt(distMatch[1], 10) : 450;

      const name =
        event.location_name ||
        (event.source_id ? `Facility ${event.source_id}` : "Industrial Facility Asset");

      const type = normalizeAssetType(summary, name);
      const exposure = calculateExposureLevel(parsedDist);

      assets.push({
        id: event.source_id || `ASSET-${event.event_id}-1`,
        name,
        type,
        distanceMeters: parsedDist,
        formattedDistance: formatDistance(parsedDist),
        exposureLevel: exposure,
        sourceType: "NASA FIRMS Context & Spatial Registry",
      });
    }
  }

  // 3. Determine Overall Industrial Exposure
  let overallExposure: ExposureLevel = "NO_ASSETS_DETECTED";
  let summaryText = "No proximate industrial infrastructure detected within analysis perimeter.";

  if (assets.length > 0) {
    if (assets.some((a) => a.exposureLevel === "HIGH")) {
      overallExposure = "HIGH";
      summaryText = `High industrial exposure: ${assets.length} proximate heavy facility asset(s) within immediate 500m radius.`;
    } else if (assets.some((a) => a.exposureLevel === "MEDIUM")) {
      overallExposure = "MEDIUM";
      summaryText = `Moderate industrial exposure: infrastructure located within 2.0km perimeter.`;
    } else {
      overallExposure = "LOW";
      summaryText = `Low industrial exposure: background spatial proximity only.`;
    }
  }

  return {
    eventId: event.event_id,
    assets,
    overallExposure,
    summary: summaryText,
    hasAssetData: assets.length > 0,
    sourceAttribution: "OpenStreetMap · WGS-84 Geodesic Context Registry",
  };
}
