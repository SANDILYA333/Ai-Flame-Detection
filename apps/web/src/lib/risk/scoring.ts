import type { ThermalEvent } from "../../types/event.ts";
import type { RiskAssessment, RiskFactor, RiskLevel } from "../../types/risk.ts";

/**
 * Computes an explainable, deterministic operational risk assessment for a canonical thermal event.
 *
 * NOTE: This is a derived frontend heuristic combining thermal radiative intensity,
 * confirmed temporal persistence, industrial proximity attribution, and sensor cluster density.
 * It is explicitly distinct from statistical ML classifier confidence.
 */
export function calculateOperationalRisk(event: ThermalEvent): RiskAssessment {
  const disclaimer =
    "Derived frontend operational heuristic · Distinct from ML model classification confidence";

  // 1. Safe Handling for Unknown / Abstained / Insufficient Information
  if (event.classification === "UNKNOWN" && event.uncertainty_state === "REVIEW_REQUIRED") {
    return {
      score: 0,
      level: "INDETERMINATE",
      isIndeterminate: true,
      indeterminateReason: "Awaiting ML Context / Classification",
      summary: "Operational risk is indeterminate pending contextual facility attribution and review.",
      factors: [
        {
          name: "Classification State",
          points: 0,
          maxPoints: 25,
          description: "Awaiting contextual intelligence (UNKNOWN classification)",
        },
        {
          name: "Uncertainty Gate",
          points: 0,
          maxPoints: 25,
          description: "Flagged as REVIEW_REQUIRED (insufficient historical baseline)",
        },
      ],
      disclaimer,
    };
  }

  const factors: RiskFactor[] = [];

  // Factor 1: Thermal Radiative Intensity (FRP) [0 - 40 points]
  const frp = typeof event.frp_mw === "number" && !isNaN(event.frp_mw) ? event.frp_mw : 0;
  let frpPoints = 5;
  let frpDesc = "Minor thermal signature (< 15 MW)";

  if (frp >= 250) {
    frpPoints = 40;
    frpDesc = `Extreme thermal radiative output (${frp.toFixed(1)} MW ≥ 250 MW)`;
  } else if (frp >= 100) {
    frpPoints = 30;
    frpDesc = `High combustion intensity (${frp.toFixed(1)} MW ≥ 100 MW)`;
  } else if (frp >= 40) {
    frpPoints = 20;
    frpDesc = `Moderate thermal output (${frp.toFixed(1)} MW ≥ 40 MW)`;
  } else if (frp >= 15) {
    frpPoints = 10;
    frpDesc = `Low-moderate anomaly (${frp.toFixed(1)} MW ≥ 15 MW)`;
  }

  factors.push({
    name: "Thermal Intensity",
    points: frpPoints,
    maxPoints: 40,
    description: frpDesc,
  });

  // Factor 2: Persistence & Temporal Recurrence [5 - 25 points]
  const isPersistent = Boolean(event.is_persistent);
  const persistencePoints = isPersistent ? 25 : 5;
  const persistenceDesc = isPersistent
    ? "Confirmed multi-day recurring thermal activity"
    : "Transient single-cycle anomaly";

  factors.push({
    name: "Temporal Persistence",
    points: persistencePoints,
    maxPoints: 25,
    description: persistenceDesc,
  });

  // Factor 3: Industrial Infrastructure Context [10 - 25 points]
  let industrialPoints = 10;
  let industrialDesc = "Non-industrial / natural background area";

  if (event.classification === "INDUSTRIAL") {
    industrialPoints = 25;
    industrialDesc = "Active petrochemical, refinery, or heavy industrial facility";
  } else if (event.classification === "UNKNOWN") {
    industrialPoints = 10;
    industrialDesc = "Unconfirmed infrastructure proximity";
  }

  factors.push({
    name: "Infrastructure Context",
    points: industrialPoints,
    maxPoints: 25,
    description: industrialDesc,
  });

  // Factor 4: Multi-Sensor Observation Cluster [2 - 10 points]
  const count = typeof event.detection_count === "number" && !isNaN(event.detection_count)
    ? event.detection_count
    : 1;
  let clusterPoints = 2;
  let clusterDesc = "Single satellite pass detection";

  if (count >= 5) {
    clusterPoints = 10;
    clusterDesc = `Dense multi-satellite observation cluster (${count} detections)`;
  } else if (count >= 2) {
    clusterPoints = 6;
    clusterDesc = `Confirmed multi-sensor detection (${count} detections)`;
  }

  factors.push({
    name: "Cluster Density",
    points: clusterPoints,
    maxPoints: 10,
    description: clusterDesc,
  });

  // Sum & Clamp Score [0 - 100]
  const rawScore = frpPoints + persistencePoints + industrialPoints + clusterPoints;
  const score = Math.min(100, Math.max(0, rawScore));

  // Determine Severity Level
  let level: RiskLevel = "LOW";
  let summary = "Low operational severity thermal anomaly.";

  if (score >= 80) {
    level = "CRITICAL";
    summary = "Critical operational severity: high-intensity persistent industrial emission.";
  } else if (score >= 60) {
    level = "HIGH";
    summary = "High operational severity: significant combustion or confirmed industrial flare.";
  } else if (score >= 35) {
    level = "MEDIUM";
    summary = "Moderate operational severity: monitor for persistence or escalation.";
  }

  return {
    score,
    level,
    factors,
    isIndeterminate: false,
    summary,
    disclaimer,
  };
}

/**
 * Returns color classes and badges for a given risk level.
 */
export function getRiskLevelStyles(level: RiskLevel): {
  bg: string;
  text: string;
  border: string;
  badgeVariant: "error" | "warning" | "industrial" | "neutral" | "success";
  label: string;
} {
  switch (level) {
    case "CRITICAL":
      return {
        bg: "bg-state-error/15",
        text: "text-state-error",
        border: "border-state-error/40",
        badgeVariant: "error",
        label: "CRITICAL",
      };
    case "HIGH":
      return {
        bg: "bg-accent/15",
        text: "text-accent",
        border: "border-accent/40",
        badgeVariant: "industrial",
        label: "HIGH",
      };
    case "MEDIUM":
      return {
        bg: "bg-state-warning/15",
        text: "text-state-warning",
        border: "border-state-warning/40",
        badgeVariant: "warning",
        label: "MEDIUM",
      };
    case "LOW":
      return {
        bg: "bg-state-success/15",
        text: "text-state-success",
        border: "border-state-success/40",
        badgeVariant: "success",
        label: "LOW",
      };
    case "INDETERMINATE":
    default:
      return {
        bg: "bg-accent-cyan/15",
        text: "text-accent-cyan",
        border: "border-accent-cyan/40",
        badgeVariant: "neutral",
        label: "INDETERMINATE",
      };
  }
}
