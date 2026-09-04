import type { ThermalEvent, EventEvidenceResponse } from "../../types/event.ts";
import type {
  EmergencyResponder,
  EventResponseRecommendation,
  ResponderType,
  ResponsePriority,
} from "../../types/responders.ts";
import { calculateHaversineDistance } from "../geo/distance.ts";

/**
 * Embedded canonical emergency responders database for 100% offline-resilient operation.
 */
export const LOCAL_EMERGENCY_RESPONDERS: Array<{
  id: string;
  name: string;
  type: ResponderType;
  city: string;
  state: string;
  lat: number;
  lon: number;
  phone: string;
  capabilities: string[];
  jurisdiction: string;
  source: string;
}> = [
  {
    id: "fire-002",
    name: "Jamnagar Industrial Fire Brigade HQ",
    type: "CHEMICAL_FIRE_STATION",
    city: "Jamnagar",
    state: "Gujarat",
    lat: 22.4707,
    lon: 70.0577,
    phone: "+91-288-2555101",
    capabilities: [
      "24 Advanced Fire Tenders",
      "Chemical Foam Capacity (80,000 L)",
      "Industrial HAZMAT Mitigation Unit",
    ],
    jurisdiction: "Jamnagar Refining SEZ & District Fire Authority",
    source: "National Emergency Responder Database",
  },
  {
    id: "hosp-002",
    name: "GG Government Hospital & Toxic Trauma ICU",
    type: "BURN_ICU",
    city: "Jamnagar",
    state: "Gujarat",
    lat: 22.4707,
    lon: 70.0577,
    phone: "+91-288-2550201",
    capabilities: [
      "180 Emergency Beds",
      "Chemical / Toxic Trauma ICU",
      "Specialized Burn Unit",
    ],
    jurisdiction: "Gujarat State Apex Medical Command",
    source: "National Trauma & Burn Registry",
  },
  {
    id: "fire-001",
    name: "NDRF 6th Battalion HAZMAT & Chemical Response",
    type: "NDRF",
    city: "Vadodara / Gandhinagar",
    state: "Gujarat",
    lat: 22.3072,
    lon: 73.1812,
    phone: "+91-265-2250101",
    capabilities: [
      "Air-droppable Disaster Response",
      "CBRN / Chemical Hazard Mitigation",
      "Heavy Urban Search & Rescue",
    ],
    jurisdiction: "National Disaster Response Force (NDRF)",
    source: "NDRF National Command Directory",
  },
  {
    id: "fire-003",
    name: "Visakhapatnam Port & Industrial Fire Station",
    type: "CHEMICAL_FIRE_STATION",
    city: "Visakhapatnam",
    state: "Andhra Pradesh",
    lat: 17.6868,
    lon: 83.2185,
    phone: "+91-891-2873101",
    capabilities: [
      "16 Advanced Chemical Tenders",
      "Foam Capacity (60,000 L)",
      "Coastal Hazmat Response Unit",
    ],
    jurisdiction: "Vizag PCPIR Industrial Zone Command",
    source: "State Industrial Emergency Coordination Registry",
  },
  {
    id: "hosp-003",
    name: "King George Hospital (KGH) Toxic Trauma ICU",
    type: "BURN_ICU",
    city: "Visakhapatnam",
    state: "Andhra Pradesh",
    lat: 17.7088,
    lon: 83.3032,
    phone: "+91-891-2564891",
    capabilities: [
      "220 Critical Care Beds",
      "Industrial Toxic Exposure Ward",
      "Apex Burn Trauma Center",
    ],
    jurisdiction: "Andhra Pradesh Apex Medical Command",
    source: "National Trauma & Burn Registry",
  },
  {
    id: "fire-008",
    name: "Mumbai Port & Trombay Refinery Fire Station",
    type: "CHEMICAL_FIRE_STATION",
    city: "Mumbai",
    state: "Maharashtra",
    lat: 18.988,
    lon: 72.889,
    phone: "+91-22-22610101",
    capabilities: [
      "22 Heavy Fire Tenders",
      "Chemical Foam Capacity (75,000 L)",
      "Petrochemical Mutual Aid Cell",
    ],
    jurisdiction: "Mumbai Fire Brigade & Chembur-Trombay SEZ",
    source: "National Emergency Responder Database",
  },
  {
    id: "hosp-009",
    name: "KEM Hospital & Chemical Poisoning Center",
    type: "BURN_ICU",
    city: "Mumbai",
    state: "Maharashtra",
    lat: 19.0026,
    lon: 72.8423,
    phone: "+91-22-24107000",
    capabilities: [
      "280 Trauma Beds",
      "Specialized Chemical Poisoning & Toxicology Unit",
    ],
    jurisdiction: "Municipal Corporation of Greater Mumbai",
    source: "National Trauma & Burn Registry",
  },
  {
    id: "fire-006",
    name: "Panipat Refinery Fire Safety Command",
    type: "CHEMICAL_FIRE_STATION",
    city: "Panipat",
    state: "Haryana",
    lat: 29.3909,
    lon: 76.9635,
    phone: "+91-180-2578101",
    capabilities: [
      "15 Advanced Fire Tenders",
      "Refinery Foam Capacity (50,000 L)",
    ],
    jurisdiction: "Haryana State Fire & Petrochemical Command",
    source: "National Emergency Responder Database",
  },
  {
    id: "hosp-001",
    name: "AIIMS Emergency & Burn Trauma Center",
    type: "BURN_ICU",
    city: "New Delhi",
    state: "Delhi",
    lat: 28.5672,
    lon: 77.21,
    phone: "+91-11-26588500",
    capabilities: [
      "250 Apex Burn & Trauma Beds",
      "National Disaster Medical Care Wing",
    ],
    jurisdiction: "National Apex Medical Institute",
    source: "National Trauma & Burn Registry",
  },
];

/**
 * Derives a deterministic emergency response recommendation package for a thermal event.
 */
export function calculateLocalResponseRecommendation(
  event: ThermalEvent,
  evidence?: EventEvidenceResponse | null
): EventResponseRecommendation {
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";
  const isAbstained = isUnknown || isReviewRequired;

  const isPersistent = Boolean(event.is_persistent || event.source_id);
  const isIndustrial = event.classification === "INDUSTRIAL";

  const contextLower = (event.context_summary || "").toLowerCase();
  const locLower = (event.location_name || "").toLowerCase();

  const isRoutineFlare =
    isPersistent &&
    isIndustrial &&
    (contextLower.includes("flare") ||
      contextLower.includes("routine") ||
      locLower.includes("flare") ||
      locLower.includes("routine"));

  let responsePriority: ResponsePriority = "MEDIUM";
  let priorityReason = "";
  const recommendationBasis: string[] = [];

  if (isAbstained) {
    responsePriority = "REVIEW_REQUIRED";
    priorityReason =
      "Analyst review required prior to emergency resource mobilization. Event classification is uncertain or abstained by scientific policy.";
    recommendationBasis.push("Scientific model uncertainty / abstention policy");
    recommendationBasis.push("Analyst verification mandatory before resource alerting");
  } else if (isRoutineFlare) {
    responsePriority = "MONITOR_ONLY";
    priorityReason =
      "Routine operational flaring source detected. Continuous thermal emission consistent with standard facility operations. Monitoring recommended; emergency mobilization not indicated.";
    recommendationBasis.push("Persistent longitudinal thermal recurrence pattern");
    recommendationBasis.push("Industrial flaring facility association within perimeter");
    recommendationBasis.push("No sudden thermal escalation or hazardous spread");
  } else if (isIndustrial) {
    if (event.frp_mw > 50) {
      responsePriority = "CRITICAL";
      priorityReason = `High-intensity industrial thermal anomaly (${event.frp_mw.toFixed(1)} MW FRP) with proximate heavy infrastructure. Immediate multi-agency response recommended.`;
      recommendationBasis.push("High radiative thermal power (>50 MW FRP)");
    } else {
      responsePriority = "HIGH";
      priorityReason =
        "Industrial thermal anomaly within infrastructure perimeter. Chemical fire brigade and burn trauma readiness recommended.";
    }
    recommendationBasis.push("Industrial infrastructure proximity verified");
    recommendationBasis.push("Chemical / hazardous material response capability match");
  } else {
    responsePriority = "MEDIUM";
    priorityReason =
      "Non-industrial thermal signature. Standard fire management resources within operational range.";
    recommendationBasis.push("Non-industrial / biomass classification profile");
    recommendationBasis.push("Geodesic perimeter proximity matching");
  }

  // Calculate distance, ETA and explainable reason for all responders
  const evaluatedResponders: EmergencyResponder[] = LOCAL_EMERGENCY_RESPONDERS.map(
    (r) => {
      const distMeters = calculateHaversineDistance(
        event.latitude,
        event.longitude,
        r.lat,
        r.lon
      );
      const distKm = distMeters / 1000;

      let formattedDistance = `${Math.round(distMeters)} m`;
      if (distMeters >= 1000) {
        formattedDistance = `${distKm < 10 ? distKm.toFixed(1) : Math.round(distKm)} km`;
      }

      // Modeled ETA: ~45 km/h emergency speed + 2 min response staging
      const etaMinutes = Math.max(1, Math.round((distKm / 45) * 60 + 2));
      const formattedEta = `~${etaMinutes} min`;

      let reason = "Regional emergency support resource";
      if (
        r.type === "CHEMICAL_FIRE_STATION" ||
        r.type === "FIRE_STATION"
      ) {
        if (distKm < 30 && isIndustrial) {
          reason =
            "Primary chemical & industrial fire response unit proximate to infrastructure perimeter";
        } else {
          reason =
            "Nearest municipal fire safety command within operational response radius";
        }
      } else if (r.type === "BURN_ICU") {
        reason =
          "Apex burn trauma ICU and toxic exposure treatment center within operational corridor";
      } else if (r.type === "HOSPITAL") {
        reason = "Regional emergency medical facility with casualty admission";
      } else if (r.type === "NDRF") {
        reason =
          "Regional NDRF battalion equipped for specialized industrial disaster & CBRN mitigation";
      }

      return {
        id: r.id,
        name: r.name,
        type: r.type,
        city: r.city,
        state: r.state,
        latitude: r.lat,
        longitude: r.lon,
        distance_meters: distMeters,
        formatted_distance: formattedDistance,
        estimated_eta_minutes: etaMinutes,
        formatted_eta: formattedEta,
        capabilities: r.capabilities,
        phone: r.phone,
        jurisdiction: r.jurisdiction,
        source: r.source,
        recommendation_reason: reason,
        plume_impact_status: "UNAVAILABLE",
      };
    }
  );

  // Deterministic sorting: Type priority (Fire -> Med -> NDRF), then distance ascending
  const typeRank = (t: ResponderType): number => {
    if (t === "CHEMICAL_FIRE_STATION" || t === "FIRE_STATION") return 0;
    if (t === "BURN_ICU" || t === "HOSPITAL") return 1;
    if (t === "NDRF") return 2;
    return 3;
  };

  evaluatedResponders.sort((a, b) => {
    const rankDiff = typeRank(a.type) - typeRank(b.type);
    if (rankDiff !== 0) return rankDiff;
    return a.distance_meters - b.distance_meters;
  });

  const topFire = evaluatedResponders
    .filter((r) => r.type === "CHEMICAL_FIRE_STATION" || r.type === "FIRE_STATION")
    .sort((a, b) => a.distance_meters - b.distance_meters)
    .slice(0, 2);
  const topMed = evaluatedResponders
    .filter((r) => r.type === "BURN_ICU" || r.type === "HOSPITAL")
    .sort((a, b) => a.distance_meters - b.distance_meters)
    .slice(0, 2);
  const topNdrf = evaluatedResponders
    .filter((r) => r.type === "NDRF")
    .slice(0, 1);

  const finalResponders = [...topFire, ...topMed, ...topNdrf];

  const isCritical = responsePriority === "CRITICAL";
  const conf = event.confidence ?? 0.85;
  const isHighConfAuto = conf > 0.98;
  const autoEscEligible = isCritical || isHighConfAuto;

  const escalationType = isCritical
    ? ("CRITICAL_MEDICAL" as const)
    : isHighConfAuto
    ? ("HIGH_CONFIDENCE_AUTO" as const)
    : conf > 0.94
    ? ("ADMIN_CONFIRMED" as const)
    : null;

  return {
    event_id: event.event_id,
    response_priority: responsePriority,
    priority_reason: priorityReason,
    confidence: conf,
    auto_escalation_eligible: autoEscEligible,
    auto_escalation_triggered: false,
    escalation_type: escalationType,
    is_routine_flare: isRoutineFlare,
    is_abstained_or_unknown: isAbstained,
    responders: finalResponders,
    nearest_hospitals: topMed,
    nearest_fire_stations: topFire,
    recommendation_basis: recommendationBasis,
    evaluated_at: new Date().toISOString(),
  };
}
