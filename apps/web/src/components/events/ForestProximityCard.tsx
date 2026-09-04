"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Trees,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Send,
  Layers,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Flame,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  fetchForestThreatForEvent,
  dispatchForestProximityAlert,
  type ForestThreatAssessmentResponse,
} from "@/lib/api/forests";
import type { ThermalEvent } from "@/types/event";

interface ForestProximityCardProps {
  event: ThermalEvent;
  className?: string;
  onForestSelect?: (forestId: string) => void;
}

export function ForestProximityCard({
  event,
  className,
  onForestSelect,
}: ForestProximityCardProps) {
  const [showAllForests, setShowAllForests] = useState(false);
  const [alertSuccessMessage, setAlertSuccessMessage] = useState<string | null>(null);
  const [threatAssessment, setThreatAssessment] = useState<ForestThreatAssessmentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);

  const loadThreatAssessment = useCallback(async () => {
    if (!event?.event_id) return;
    setIsLoading(true);
    setIsError(false);
    try {
      const data = await fetchForestThreatForEvent(event.event_id);
      setThreatAssessment(data);
    } catch (err) {
      console.warn("Forest threat fetch non-critical error:", err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  }, [event?.event_id]);

  useEffect(() => {
    loadThreatAssessment();
  }, [loadThreatAssessment]);

  const handleDispatchAlert = async (targetForestId: string) => {
    if (!event?.event_id || isDispatching) return;
    setIsDispatching(true);
    try {
      const res = await dispatchForestProximityAlert({
        event_id: event.event_id,
        forest_id: targetForestId,
        fire_confidence: event.confidence <= 1 ? event.confidence * 100 : event.confidence,
        channels: ["sms", "whatsapp"],
        force_dispatch: false,
      });

      setAlertSuccessMessage(
        res.notification_dispatched
          ? `Alert dispatched to Forest Rangers via SMS/WhatsApp (${res.threat_level})`
          : `Proximity logged: ${res.threat_level} (${res.distance_km.toFixed(2)} km)`
      );
      loadThreatAssessment();
      setTimeout(() => setAlertSuccessMessage(null), 6000);
    } catch (err: any) {
      setAlertSuccessMessage(`Alert dispatch failed: ${err?.message || "Unknown error"}`);
      setTimeout(() => setAlertSuccessMessage(null), 6000);
    } finally {
      setIsDispatching(false);
    }
  };

  if (isLoading) {
    return (
      <div className={cn("p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2 animate-pulse", className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-foreground-muted">
            <Trees className="w-3.5 h-3.5 text-state-warning" />
            <span className="text-[10px] uppercase font-bold">Forest Proximity Intelligence</span>
          </div>
          <span className="text-[9px] text-foreground-muted">Computing Boundary Geodesics...</span>
        </div>
        <div className="h-10 bg-surface-hover/60 rounded-control" />
      </div>
    );
  }

  if (isError || !threatAssessment) {
    return (
      <div className={cn("p-2.5 rounded-control bg-surface/90 border border-border/80 font-mono space-y-1.5", className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-foreground-muted">
            <Trees className="w-3.5 h-3.5 text-foreground-muted" />
            <span className="text-[10px] uppercase font-bold">Forest Proximity Intelligence</span>
          </div>
          <button
            onClick={() => loadThreatAssessment()}
            className="text-[9px] text-accent hover:underline"
          >
            Retry
          </button>
        </div>
        <p className="text-[10px] text-foreground-muted">
          No nearby forest spatial data available for this coordinate.
        </p>
      </div>
    );
  }

  const { nearest_forest, threat_level, is_threatened, nearby_forests, total_threatened_forests } = threatAssessment;

  // Threat level badge styling
  const getThreatBadge = (level: string) => {
    switch (level) {
      case "INSIDE_FOREST":
        return {
          label: "INSIDE FOREST BOUNDARY",
          badgeClass: "bg-red-500/20 text-red-400 border-red-500/50 animate-pulse",
          icon: <Flame className="w-3 h-3 text-red-400 animate-bounce" />,
        };
      case "CRITICAL":
        return {
          label: "CRITICAL PROXIMITY (<2 km)",
          badgeClass: "bg-state-error/20 text-state-error border-state-error/50",
          icon: <AlertTriangle className="w-3 h-3 text-state-error" />,
        };
      case "WARNING":
      case "HIGH":
        return {
          label: "WARNING ZONE (2-5 km)",
          badgeClass: "bg-state-warning/20 text-state-warning border-state-warning/50",
          icon: <AlertTriangle className="w-3 h-3 text-state-warning" />,
        };
      case "AWARENESS":
      case "MODERATE":
        return {
          label: "AWARENESS ZONE (5-10 km)",
          badgeClass: "bg-blue-500/20 text-blue-400 border-blue-500/40",
          icon: <ShieldAlert className="w-3 h-3 text-blue-400" />,
        };
      case "NONE":
      default:
        return {
          label: "OUTSIDE THREAT RADIUS (>10 km)",
          badgeClass: "bg-surface-hover text-foreground-muted border-border",
          icon: <ShieldCheck className="w-3 h-3 text-emerald-400" />,
        };
    }
  };

  const threatBadge = getThreatBadge(threat_level);

  return (
    <div
      data-testid="forest-proximity-card"
      className={cn(
        "p-3 rounded-control font-mono space-y-2.5 shadow-sm border transition-all duration-200",
        threat_level === "INSIDE_FOREST"
          ? "bg-red-950/20 border-red-500/40"
          : threat_level === "CRITICAL"
          ? "bg-state-error/10 border-state-error/40"
          : threat_level === "WARNING"
          ? "bg-state-warning/10 border-state-warning/40"
          : "bg-surface/90 border-border/80",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <Trees
            className={cn(
              "w-4 h-4 shrink-0",
              threat_level === "INSIDE_FOREST" || threat_level === "CRITICAL"
                ? "text-state-error animate-pulse"
                : is_threatened
                ? "text-state-warning"
                : "text-emerald-400"
            )}
          />
          <span className="text-[11px] font-bold text-foreground uppercase tracking-wider truncate">
            FOREST PROXIMITY & THREAT
          </span>
        </div>
        <span
          className={cn(
            "text-[9px] px-2 py-0.5 rounded border font-bold uppercase shrink-0 flex items-center gap-1",
            threatBadge.badgeClass
          )}
        >
          {threatBadge.icon}
          <span>{threatBadge.label}</span>
        </span>
      </div>

      {/* Nearest Forest Details */}
      {nearest_forest ? (
        <div className="space-y-2">
          <div className="bg-background/90 p-2.5 rounded-control border border-border/60 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs font-bold text-foreground truncate">
                  {nearest_forest.name || "Unnamed Forest Stand"}
                </div>
                <div className="text-[10px] text-foreground-muted flex items-center gap-2 mt-0.5">
                  <span className="capitalize">{nearest_forest.forest_type.replace("_", " ")}</span>
                  <span>•</span>
                  <span>{nearest_forest.osm_tag}</span>
                  <span>•</span>
                  <span>{nearest_forest.country_code}</span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div
                  className={cn(
                    "text-xs font-bold font-mono",
                    nearest_forest.inside_forest
                      ? "text-red-400"
                      : nearest_forest.distance_km < 2.0
                      ? "text-state-error"
                      : nearest_forest.distance_km < 5.0
                      ? "text-state-warning"
                      : "text-foreground"
                  )}
                >
                  {nearest_forest.inside_forest
                    ? "0.00 km (INSIDE)"
                    : `${nearest_forest.distance_km.toFixed(2)} km`}
                </div>
                <div className="text-[9px] text-foreground-muted">to Boundary</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1.5 border-t border-border/40 text-[10px]">
              <div>
                <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
                  Forest Area
                </span>
                <span className="font-semibold text-foreground">
                  {nearest_forest.area_km2.toFixed(2)} km²
                </span>
              </div>
              <div>
                <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
                  Threat Classification
                </span>
                <span
                  className={cn(
                    "font-semibold uppercase",
                    nearest_forest.threat_level === "INSIDE_FOREST"
                      ? "text-red-400 font-bold"
                      : nearest_forest.threat_level === "CRITICAL"
                      ? "text-state-error font-bold"
                      : nearest_forest.threat_level === "WARNING"
                      ? "text-state-warning font-bold"
                      : "text-foreground"
                  )}
                >
                  {nearest_forest.threat_level}
                </span>
              </div>
            </div>
          </div>

          {/* Action Button: Dispatch Forest Ranger Alert */}
          {is_threatened && (
            <div className="pt-0.5 space-y-1.5">
              <button
                type="button"
                onClick={() => handleDispatchAlert(nearest_forest.forest_id)}
                disabled={isDispatching}
                className={cn(
                  "w-full py-2 px-3 rounded-control font-bold text-xs flex items-center justify-center gap-1.5 transition-all active:scale-95 shadow-sm",
                  threat_level === "INSIDE_FOREST" || threat_level === "CRITICAL"
                    ? "bg-state-error hover:bg-state-error/90 text-white disabled:opacity-50"
                    : "bg-state-warning hover:bg-state-warning/90 text-background disabled:opacity-50"
                )}
              >
                <Send className="w-3.5 h-3.5" />
                <span>
                  {isDispatching
                    ? "DISPATCHING RANGER ALERT..."
                    : threat_level === "INSIDE_FOREST"
                    ? "DISPATCH IMMEDIATE FOREST SUPPRESSION ALERT"
                    : "DISPATCH FOREST RANGER PROXIMITY ALERT"}
                </span>
              </button>

              {alertSuccessMessage && (
                <div className="text-[10px] p-1.5 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 rounded flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                  <span>{alertSuccessMessage}</span>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="text-[10px] text-foreground-muted p-2 bg-background/80 rounded border border-border/50">
          No forest geometries detected within 100 km of thermal anomaly.
        </div>
      )}

      {/* Multiple Nearby Forests Collapsible */}
      {nearby_forests && nearby_forests.length > 1 && (
        <div className="pt-1 border-t border-border/40">
          <button
            type="button"
            onClick={() => setShowAllForests((prev) => !prev)}
            className="w-full text-[10px] text-foreground-muted hover:text-foreground flex items-center justify-between py-1 transition-colors"
          >
            <span className="flex items-center gap-1">
              <Layers className="w-3 h-3 text-foreground-muted" />
              <span>
                Nearby Forest Zones ({nearby_forests.length} detected, {total_threatened_forests} threatened)
              </span>
            </span>
            {showAllForests ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showAllForests && (
            <div className="space-y-1.5 mt-1.5 max-h-36 overflow-y-auto pr-1 scrollbar-thin">
              {nearby_forests.map((f) => (
                <div
                  key={f.forest_id}
                  onClick={() => onForestSelect?.(f.forest_id)}
                  className={cn(
                    "p-1.5 rounded bg-surface border border-border/50 text-[9.5px] flex items-center justify-between hover:bg-surface-hover cursor-pointer transition-colors",
                    f.threat_level === "INSIDE_FOREST"
                      ? "border-red-500/40"
                      : f.threat_level === "CRITICAL"
                      ? "border-state-error/40"
                      : f.threat_level === "WARNING"
                      ? "border-state-warning/40"
                      : "border-border/40"
                  )}
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-bold text-foreground truncate">
                      {f.name || "Forest Tract"}
                    </div>
                    <div className="text-foreground-muted text-[8.5px]">
                      {f.area_km2.toFixed(1)} km² • {f.forest_type.replace("_", " ")}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={cn(
                        "font-mono font-bold",
                        f.inside_forest
                          ? "text-red-400"
                          : f.distance_km < 2
                          ? "text-state-error"
                          : f.distance_km < 5
                          ? "text-state-warning"
                          : "text-foreground-muted"
                      )}
                    >
                      {f.inside_forest ? "INSIDE" : `${f.distance_km.toFixed(1)} km`}
                    </span>
                    <span className="block text-[8px] text-foreground-muted uppercase">
                      {f.threat_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
