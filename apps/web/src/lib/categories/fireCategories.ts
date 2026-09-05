import type { ThermalEvent } from "../../types/event.ts";
import { calculateOperationalRisk } from "../risk/scoring.ts";

export type FireCategoryType =
  | "ALL"
  | "WILDFIRE"
  | "INDUSTRIAL"
  | "HOTSPOT"
  | "PERSISTENT"
  | "AGRICULTURAL"
  | "REVIEW_REQUIRED";

export interface FireCategoryConfig {
  id: FireCategoryType;
  title: string;
  shortLabel: string;
  description: string;
  iconName: string;
  accentColor: string;
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
}

export const FIRE_CATEGORIES: FireCategoryConfig[] = [
  {
    id: "WILDFIRE",
    title: "Wildfires & Forest Fires",
    shortLabel: "Wildfires",
    description: "Active vegetation canopy, forest tract & woodland brush combustion",
    iconName: "Trees",
    accentColor: "#34c759",
    badgeBg: "bg-[#34c759]/10",
    badgeBorder: "border-[#34c759]/30",
    badgeText: "text-[#34c759]",
  },
  {
    id: "INDUSTRIAL",
    title: "Industrial & Facility Fires",
    shortLabel: "Industrial",
    description: "Refinery flaring, exhaust stacks, blast furnaces & chemical plants",
    iconName: "Factory",
    accentColor: "#39ff88",
    badgeBg: "bg-[#39ff88]/10",
    badgeBorder: "border-[#39ff88]/30",
    badgeText: "text-[#39ff88]",
  },
  {
    id: "HOTSPOT",
    title: "Thermal Hotspots & Anomalies",
    shortLabel: "Hotspots",
    description: "High-temperature ground surface radiative anomalies & metallurgical heat",
    iconName: "Flame",
    accentColor: "#ff9500",
    badgeBg: "bg-[#ff9500]/10",
    badgeBorder: "border-[#ff9500]/30",
    badgeText: "text-[#ff9500]",
  },
  {
    id: "PERSISTENT",
    title: "Persistent Thermal Sources",
    shortLabel: "Persistent",
    description: "Chronic multi-observation flaring and continuous industrial thermal emitters",
    iconName: "Clock",
    accentColor: "#af52de",
    badgeBg: "bg-[#af52de]/10",
    badgeBorder: "border-[#af52de]/30",
    badgeText: "text-[#af52de]",
  },
  {
    id: "AGRICULTURAL",
    title: "Agricultural & Rural Burns",
    shortLabel: "Agricultural",
    description: "Post-harvest crop residue, stubble management & rural open burning",
    iconName: "Tractor",
    accentColor: "#ffd60a",
    badgeBg: "bg-[#ffd60a]/10",
    badgeBorder: "border-[#ffd60a]/30",
    badgeText: "text-[#ffd60a]",
  },
  {
    id: "REVIEW_REQUIRED",
    title: "Uncertain / Review Required",
    shortLabel: "Review Required",
    description: "Indeterminate sensor signals, low confidence or abstained AI predictions",
    iconName: "HelpCircle",
    accentColor: "#00d9ff",
    badgeBg: "bg-[#00d9ff]/10",
    badgeBorder: "border-[#00d9ff]/30",
    badgeText: "text-[#00d9ff]",
  },
];

/**
 * Determines whether a ThermalEvent belongs to a specific category
 */
export function isEventInCategory(event: ThermalEvent, categoryId: FireCategoryType): boolean {
  if (categoryId === "ALL") return true;

  const phenomenon = (event.phenomenon || "").toUpperCase();
  const classification = (event.classification || "").toUpperCase();
  const context = (event.context_summary || "").toLowerCase();
  const loc = (event.location_name || "").toLowerCase();

  switch (categoryId) {
    case "WILDFIRE":
      return (
        phenomenon === "VEGETATION_WILDFIRE" ||
        context.includes("forest") ||
        context.includes("woodland") ||
        context.includes("vegetation") ||
        loc.includes("forest") ||
        loc.includes("wildfire") ||
        loc.includes("reserve") ||
        loc.includes("national park")
      );

    case "INDUSTRIAL":
      return (
        classification === "INDUSTRIAL" ||
        phenomenon === "FLARE" ||
        phenomenon === "STACK" ||
        phenomenon === "INDUSTRIAL_THERMAL_SOURCE"
      );

    case "HOTSPOT":
      return (
        phenomenon === "HOT_SURFACE" ||
        phenomenon === "OTHER_THERMAL_ANOMALY" ||
        event.frp_mw >= 100 ||
        context.includes("smelting") ||
        context.includes("slag")
      );

    case "PERSISTENT":
      return Boolean(event.is_persistent);

    case "AGRICULTURAL":
      return (
        phenomenon === "AGRICULTURAL_BURN" ||
        (classification === "NON_INDUSTRIAL" &&
          !context.includes("forest") &&
          !context.includes("woodland") &&
          !loc.includes("forest"))
      );

    case "REVIEW_REQUIRED":
      return (
        classification === "UNKNOWN" ||
        event.uncertainty_state === "REVIEW_REQUIRED" ||
        event.uncertainty_state === "ABSTAINED" ||
        event.confidence < 0.7
      );

    default:
      return true;
  }
}

/**
 * Classifies an event into its primary display category
 */
export function derivePrimaryCategory(event: ThermalEvent): FireCategoryType {
  if (
    event.classification === "UNKNOWN" ||
    event.uncertainty_state === "REVIEW_REQUIRED" ||
    event.confidence < 0.7
  ) {
    return "REVIEW_REQUIRED";
  }

  const context = (event.context_summary || "").toLowerCase();
  const loc = (event.location_name || "").toLowerCase();
  const phenomenon = (event.phenomenon || "").toUpperCase();

  if (
    phenomenon === "VEGETATION_WILDFIRE" ||
    context.includes("forest") ||
    context.includes("woodland") ||
    loc.includes("forest")
  ) {
    return "WILDFIRE";
  }

  if (phenomenon === "AGRICULTURAL_BURN" || event.classification === "NON_INDUSTRIAL") {
    return "AGRICULTURAL";
  }

  if (event.is_persistent) {
    return "PERSISTENT";
  }

  if (phenomenon === "HOT_SURFACE" || event.frp_mw > 150) {
    return "HOTSPOT";
  }

  return "INDUSTRIAL";
}

export interface CategorySummaryMetrics {
  categoryId: FireCategoryType;
  title: string;
  totalCount: number;
  activeCount: number;
  criticalCount: number;
  highCount: number;
  maxFrp: number;
  latestTimestamp: string | null;
}

/**
 * Computes category breakdown metrics across a set of events
 */
export function computeCategoryMetrics(events: ThermalEvent[]): Record<FireCategoryType, CategorySummaryMetrics> {
  const result: Record<FireCategoryType, CategorySummaryMetrics> = {
    ALL: {
      categoryId: "ALL",
      title: "All Thermal Incidents",
      totalCount: events.length,
      activeCount: events.length,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    WILDFIRE: {
      categoryId: "WILDFIRE",
      title: "Wildfires & Forest Fires",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    INDUSTRIAL: {
      categoryId: "INDUSTRIAL",
      title: "Industrial & Facility Fires",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    HOTSPOT: {
      categoryId: "HOTSPOT",
      title: "Thermal Hotspots & Anomalies",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    PERSISTENT: {
      categoryId: "PERSISTENT",
      title: "Persistent Thermal Sources",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    AGRICULTURAL: {
      categoryId: "AGRICULTURAL",
      title: "Agricultural & Rural Burns",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
    REVIEW_REQUIRED: {
      categoryId: "REVIEW_REQUIRED",
      title: "Uncertain / Review Required",
      totalCount: 0,
      activeCount: 0,
      criticalCount: 0,
      highCount: 0,
      maxFrp: 0,
      latestTimestamp: null,
    },
  };

  events.forEach((evt) => {
    const risk = calculateOperationalRisk(evt);
    const isCritical = risk.level === "CRITICAL";
    const isHigh = risk.level === "HIGH";

    // Update ALL
    if (isCritical) result.ALL.criticalCount++;
    if (isHigh) result.ALL.highCount++;
    if (evt.frp_mw > result.ALL.maxFrp) result.ALL.maxFrp = evt.frp_mw;
    if (!result.ALL.latestTimestamp || new Date(evt.end_time) > new Date(result.ALL.latestTimestamp)) {
      result.ALL.latestTimestamp = evt.end_time;
    }

    FIRE_CATEGORIES.forEach((cat) => {
      if (isEventInCategory(evt, cat.id)) {
        const entry = result[cat.id];
        entry.totalCount++;
        entry.activeCount++;
        if (isCritical) entry.criticalCount++;
        if (isHigh) entry.highCount++;
        if (evt.frp_mw > entry.maxFrp) entry.maxFrp = evt.frp_mw;
        if (!entry.latestTimestamp || new Date(evt.end_time) > new Date(entry.latestTimestamp)) {
          entry.latestTimestamp = evt.end_time;
        }
      }
    });
  });

  return result;
}
