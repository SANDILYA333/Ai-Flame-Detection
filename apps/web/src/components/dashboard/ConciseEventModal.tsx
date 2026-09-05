"use client";

import React, { useEffect, useMemo } from "react";
import {
  X,
  Flame,
  MapPin,
  Clock,
  Zap,
  ShieldCheck,
  Layers,
  Satellite,
  ArrowRight,
  Radio,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import { formatCoordinate } from "@/lib/format/coordinates";
import { derivePrimaryCategory } from "@/lib/categories/fireCategories";
import { formatHumanReadableLocation } from "@/lib/location/locationFilter";
import { cn } from "@/lib/utils";

export function ConciseEventModal() {
  const {
    conciseSelectedEvent,
    isConciseDetailOpen,
    closeConciseEventDetails,
    openDetailedAnalysis,
  } = useEventContext();

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isConciseDetailOpen) {
        closeConciseEventDetails();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isConciseDetailOpen, closeConciseEventDetails]);

  if (!isConciseDetailOpen || !conciseSelectedEvent) return null;

  const event = conciseSelectedEvent;
  const risk = calculateOperationalRisk(event);
  const primaryCategory = derivePrimaryCategory(event);
  const formattedCoords = formatCoordinate(event.latitude, event.longitude);

  const severityStyles =
    risk.level === "CRITICAL"
      ? "bg-state-error/15 text-state-error border-state-error/40"
      : risk.level === "HIGH"
      ? "bg-state-warning/15 text-state-warning border-state-warning/40"
      : risk.level === "MEDIUM"
      ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
      : "bg-accent/15 text-accent border-accent/40";

  // Format friendly detection time
  const formattedDetectionTime = (() => {
    try {
      const d = new Date(event.start_time);
      return `${d.getUTCHours().toString().padStart(2, "0")}:${d.getUTCMinutes().toString().padStart(2, "0")} UTC`;
    } catch {
      return "Active";
    }
  })();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-150 font-mono select-none"
      onClick={closeConciseEventDetails}
    >
      <div
        className="relative w-full max-w-lg bg-surface border border-border rounded-panel shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="h-12 px-4 bg-surface-raised border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-control bg-thermal/15 border border-thermal/30 flex items-center justify-center text-thermal">
              <Flame className="w-3.5 h-3.5 animate-flame" />
            </div>
            <div>
              <span className="text-xs font-bold text-foreground">
                FIRE EVENT #{event.event_id}
              </span>
            </div>
          </div>

          <button
            onClick={closeConciseEventDetails}
            aria-label="Close modal"
            className="w-7 h-7 rounded-control flex items-center justify-center text-foreground-muted hover:text-foreground hover:bg-surface-hover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 flex flex-col gap-4 text-xs">
          {/* Top Banner: Location & Severity */}
          <div className="flex items-start justify-between gap-3 p-3 rounded-control bg-surface-raised border border-border">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-thermal shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-foreground leading-tight">
                  {formatHumanReadableLocation(event)}
                </h3>
                <span className="text-[11px] text-accent font-semibold">
                  Coordinates: {formattedCoords}
                </span>
              </div>
            </div>

            <span
              className={cn(
                "px-2.5 py-1 rounded text-xs font-bold uppercase border shrink-0",
                severityStyles
              )}
            >
              {risk.level} SEVERITY
            </span>
          </div>

          {/* Key 5 Dimension Grid: WHAT, HOW SERIOUS, WHEN, HOW CONFIDENT */}
          <div className="grid grid-cols-2 gap-2.5">
            {/* 1. WHAT */}
            <div className="p-2.5 rounded-control bg-surface-raised/60 border border-border/80 flex flex-col">
              <span className="text-[10px] text-foreground-muted uppercase tracking-wider mb-1 flex items-center gap-1">
                <Layers className="w-3 h-3 text-accent-cyan" />
                Classification
              </span>
              <span className="text-xs font-bold text-foreground">
                {event.classification === "NON_INDUSTRIAL"
                  ? "Non-Industrial / Wildfire"
                  : event.classification === "INDUSTRIAL"
                  ? "Industrial Facility"
                  : "Uncertain / Unknown"}
              </span>
              <span className="text-[10px] text-foreground-secondary mt-0.5">
                Type: {primaryCategory} · {event.phenomenon}
              </span>
            </div>

            {/* 2. HOW SERIOUS */}
            <div className="p-2.5 rounded-control bg-surface-raised/60 border border-border/80 flex flex-col">
              <span className="text-[10px] text-foreground-muted uppercase tracking-wider mb-1 flex items-center gap-1">
                <Zap className="w-3 h-3 text-thermal" />
                Radiative Power (FRP)
              </span>
              <span className="text-xs font-bold text-thermal">
                {event.frp_mw.toFixed(1)} MW
              </span>
              <span className="text-[10px] text-foreground-secondary mt-0.5">
                {event.detection_count} Satellite Detections
              </span>
            </div>

            {/* 3. WHEN */}
            <div className="p-2.5 rounded-control bg-surface-raised/60 border border-border/80 flex flex-col">
              <span className="text-[10px] text-foreground-muted uppercase tracking-wider mb-1 flex items-center gap-1">
                <Clock className="w-3 h-3 text-accent" />
                Detected
              </span>
              <span className="text-[11px] font-semibold text-foreground truncate">
                {formattedDetectionTime}
              </span>
              <span className="text-[10px] text-accent font-semibold mt-0.5">
                Status: ACTIVE
              </span>
            </div>

            {/* 4. HOW CONFIDENT */}
            <div className="p-2.5 rounded-control bg-surface-raised/60 border border-border/80 flex flex-col">
              <span className="text-[10px] text-foreground-muted uppercase tracking-wider mb-1 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-accent-cyan" />
                AI Confidence
              </span>
              <span className="text-xs font-bold text-accent">
                {(event.confidence * 100).toFixed(1)}% Confidence
              </span>
              <span className="text-[10px] text-foreground-secondary mt-0.5">
                Status: {event.uncertainty_state}
              </span>
            </div>
          </div>

          {/* Context Summary */}
          {event.context_summary && (
            <div className="p-2.5 rounded-control bg-base border border-border text-[11px] text-foreground-secondary leading-relaxed">
              <span className="text-foreground font-semibold">Context: </span>
              {event.context_summary}
            </div>
          )}

          {/* Instrument provenance */}
          <div className="flex items-center justify-between text-[10px] text-foreground-muted px-1">
            <span className="flex items-center gap-1">
              <Satellite className="w-3 h-3 text-accent-cyan" />
              {event.satellite_instrument || "VIIRS NOAA-20 / SNPP"}
            </span>
            <span className="flex items-center gap-1">
              <Radio className="w-3 h-3 text-accent" />
              WGS-84 EPSG:4326
            </span>
          </div>
        </div>

        {/* Primary Action Footer: OPEN DETAILED ANALYSIS */}
        <div className="p-4 bg-surface-raised border-t border-border flex items-center justify-between gap-3">
          <button
            onClick={closeConciseEventDetails}
            className="px-3.5 py-2 text-xs text-foreground-muted hover:text-foreground font-semibold rounded-control transition-colors"
          >
            Close
          </button>

          <button
            onClick={() => openDetailedAnalysis(event)}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-background bg-accent hover:bg-accent-hover rounded-control transition-all shadow-md active:scale-98 glow-accent"
          >
            <Flame className="w-4 h-4 text-background" />
            <span>OPEN DETAILED ANALYSIS</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
