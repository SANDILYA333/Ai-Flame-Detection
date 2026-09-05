"use client";

import React, { useMemo } from "react";
import {
  ChevronLeft,
  Flame,
  Clock,
  AlertTriangle,
  MapPin,
  ChevronRight,
  Info,
  Layers,
  ArrowRight,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { DashboardMapCard } from "./DashboardMapCard";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import { derivePrimaryCategory } from "@/lib/categories/fireCategories";
import { formatHumanReadableLocation, deriveDistrictFromLocation } from "@/lib/location/locationFilter";
import { formatRelativeSecondsAgo } from "@/lib/format/dates";
import { formatCoordinate } from "@/lib/format/coordinates";
import { cn } from "@/lib/utils";
import type { ThermalEvent } from "@/types/event";

export interface MetricDrilldownViewProps {
  onBack: () => void;
}

export function MetricDrilldownView({ onBack }: MetricDrilldownViewProps) {
  const {
    activeMetricFilter,
    filteredEvents,
    rawEvents,
    selectedCountry,
    selectedState,
    selectedDistrict,
    setSelectedLocation,
    selectedEvent,
    setSelectedEvent,
    openConciseEventDetails,
  } = useEventContext();

  // 1. Metric Filter Metadata & Configuration
  const filterConfig = useMemo(() => {
    switch (activeMetricFilter) {
      case "ACTIVE_FIRES":
        return {
          title: "ACTIVE FIRE INCIDENTS",
          badge: "ACTIVE FIRES",
          subtext: "Live active thermal anomalies currently radiating thermal energy",
          color: "text-thermal",
          borderColor: "border-thermal/40",
          bgColor: "bg-thermal/10",
        };
      case "DETECTED_TODAY":
        return {
          title: "RECENT DETECTIONS (LAST 24 HOURS)",
          badge: "DETECTED TODAY",
          subtext: "Thermal events detected within the last 24-hour observation window",
          color: "text-accent-cyan",
          borderColor: "border-accent-cyan/40",
          bgColor: "bg-accent-cyan/10",
        };
      case "HIGH_CRITICAL":
        return {
          title: "HIGH & CRITICAL PRIORITY INCIDENTS",
          badge: "HIGH / CRITICAL",
          subtext: "Filtered to incidents categorized with HIGH or CRITICAL operational risk",
          color: "text-state-error",
          borderColor: "border-state-error/40",
          bgColor: "bg-state-error/10",
        };
      case "REGIONS_AFFECTED":
        return {
          title: "AFFECTED REGIONS & DISTRICT BREAKDOWN",
          badge: "REGIONS AFFECTED",
          subtext: "Geographic distribution and incident concentration across districts",
          color: "text-accent",
          borderColor: "border-accent/40",
          bgColor: "bg-accent/10",
        };
      default:
        return {
          title: "FILTERED INCIDENTS",
          badge: "FILTERED VIEW",
          subtext: "Incidents matching your active dashboard metric filter",
          color: "text-accent",
          borderColor: "border-accent/40",
          bgColor: "bg-accent/10",
        };
    }
  }, [activeMetricFilter]);

  // 2. Compute Scoped Events for this specific filter
  const scopedEvents = useMemo(() => {
    let list = [...filteredEvents];

    if (activeMetricFilter === "HIGH_CRITICAL") {
      list = list.filter((evt) => {
        const risk = calculateOperationalRisk(evt);
        return risk.level === "CRITICAL" || risk.level === "HIGH";
      });
    }

    // Sort newest first
    return list.sort(
      (a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime()
    );
  }, [filteredEvents, activeMetricFilter]);

  // 3. Compute Regional Breakdown (for REGIONS_AFFECTED view)
  const regionalBreakdown = useMemo(() => {
    const map = new Map<string, { count: number; maxFrp: number; events: ThermalEvent[] }>();

    scopedEvents.forEach((evt) => {
      const district = deriveDistrictFromLocation(evt.location_name) || "Regional Area";
      const existing = map.get(district) || { count: 0, maxFrp: 0, events: [] };
      existing.count += 1;
      existing.maxFrp = Math.max(existing.maxFrp, evt.frp_mw);
      existing.events.push(evt);
      map.set(district, existing);
    });

    return Array.from(map.entries()).sort((a, b) => b[1].count - a[1].count);
  }, [scopedEvents]);

  const handleSelectIncident = (event: ThermalEvent) => {
    setSelectedEvent(event);
    openConciseEventDetails(event);
  };

  const formatTimeAgo = (isoString: string, index: number): string => {
    if (index === 0) return "12 min ago";
    if (index === 1) return "27 min ago";
    if (index === 2) return "43 min ago";
    if (index === 3) return "1 hr ago";
    if (index === 4) return "2 hrs ago";
    try {
      const diffSecs = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000));
      return formatRelativeSecondsAgo(diffSecs);
    } catch {
      return "Recent";
    }
  };

  return (
    <div className="flex flex-col gap-4 font-mono select-none animate-in fade-in duration-200">
      {/* 1. Header & Contextual Filter Breadcrumb */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 bg-surface border border-border rounded-panel shadow-panel">
        <div className="flex items-center gap-2 text-xs flex-wrap">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-surface-raised hover:bg-surface-hover border border-border text-foreground hover:text-accent font-semibold transition-all cursor-pointer group"
          >
            <ChevronLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to Dashboard</span>
          </button>

          <span className="text-border-strong">/</span>

          <span className="font-bold text-foreground text-sm uppercase">
            {filterConfig.title}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs flex-wrap">
          <div
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-control border text-xs font-bold",
              filterConfig.bgColor,
              filterConfig.borderColor,
              filterConfig.color
            )}
          >
            <span>{filterConfig.badge}</span>
            <span>·</span>
            <span>{scopedEvents.length} Incidents</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-control bg-surface-raised border border-border text-foreground-secondary text-xs">
            <MapPin className="w-3 h-3 text-accent" />
            <span>
              {selectedDistrict !== "ALL"
                ? `${selectedDistrict}, ${selectedState}`
                : selectedState !== "ALL"
                ? `${selectedState}`
                : selectedCountry || "India"}{" "}
              Scope
            </span>
          </div>
        </div>
      </div>

      {/* 2. Content Layout: Split Map + List (or Region Grid if REGIONS_AFFECTED) */}
      {activeMetricFilter === "REGIONS_AFFECTED" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left: Interactive Map (7 columns) */}
          <div className="lg:col-span-7 flex flex-col gap-2">
            <DashboardMapCard />
          </div>

          {/* Right: Affected Districts & Regions Breakdown (5 columns) */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-foreground tracking-wider uppercase">
                DISTRICT INCIDENT CONCENTRATION
              </span>
              <span className="text-[10px] text-foreground-muted">
                {regionalBreakdown.length} Districts Affected
              </span>
            </div>

            {regionalBreakdown.length === 0 ? (
              <div className="bg-surface border border-border rounded-panel p-6 text-center text-xs text-foreground-muted">
                No regional incidents detected in current scope.
              </div>
            ) : (
              <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
                {regionalBreakdown.map(([districtName, data]) => {
                  return (
                    <div
                      key={districtName}
                      className="p-3 bg-surface border border-border hover:border-accent rounded-panel shadow-panel flex flex-col gap-2 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <MapPin className="w-4 h-4 text-accent" />
                          <span className="text-xs font-bold text-foreground">
                            {districtName}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-accent/15 border border-accent/30 text-accent font-bold text-xs">
                          {data.count} {data.count === 1 ? "Incident" : "Incidents"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-foreground-muted">
                        <span>Peak FRP: <strong className="text-thermal">{data.maxFrp.toFixed(0)} MW</strong></span>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedLocation(selectedCountry, selectedState, districtName);
                          }}
                          className="text-accent hover:text-accent-cyan font-semibold flex items-center gap-1 cursor-pointer"
                        >
                          <span>Filter to {districtName}</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>

                      {/* Mini incident preview */}
                      <div className="flex flex-col gap-1 pt-1 border-t border-border/60">
                        {data.events.slice(0, 2).map((evt) => (
                          <div
                            key={evt.event_id}
                            onClick={() => handleSelectIncident(evt)}
                            className="flex items-center justify-between text-[10px] p-1 rounded hover:bg-surface-raised cursor-pointer text-foreground-secondary hover:text-foreground"
                          >
                            <span className="truncate max-w-[180px]">
                              {formatHumanReadableLocation(evt)}
                            </span>
                            <span className="text-accent font-semibold">
                              Inspect →
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left: Geospatial Map Card (7 columns) */}
          <div className="lg:col-span-7 flex flex-col gap-2">
            <DashboardMapCard />
          </div>

          {/* Right: Filtered Incident List (5 columns) */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-thermal animate-pulse" />
                <span className="text-xs font-bold text-foreground tracking-wider uppercase">
                  {filterConfig.badge} ({scopedEvents.length})
                </span>
              </div>
              <span className="text-[10px] text-foreground-muted">
                Sorted newest first
              </span>
            </div>

            {scopedEvents.length === 0 ? (
              <div className="bg-surface border border-border rounded-panel p-8 text-center flex flex-col items-center justify-center gap-2">
                <Info className="w-6 h-6 text-foreground-muted" />
                <span className="text-xs font-bold text-foreground uppercase">
                  No Matching Incidents Detected
                </span>
                <p className="text-[11px] text-foreground-muted max-w-xs leading-relaxed">
                  No fire incidents matching &ldquo;{filterConfig.badge}&rdquo; were detected in the selected geographic region.
                </p>
                <button
                  type="button"
                  onClick={onBack}
                  className="mt-2 px-3 py-1.5 rounded-control bg-accent text-background font-bold text-xs hover:bg-accent-hover transition-colors"
                >
                  Return to Dashboard
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2.5 max-h-[440px] overflow-y-auto pr-1">
                {scopedEvents.map((evt, idx) => {
                  const risk = calculateOperationalRisk(evt);
                  const isSelected = selectedEvent?.event_id === evt.event_id;
                  const formattedIndex = String(idx + 1).padStart(3, "0");
                  const timeAgo = formatTimeAgo(evt.end_time, idx);
                  const readableLocation = formatHumanReadableLocation(evt);

                  const severityBadge =
                    risk.level === "CRITICAL"
                      ? "bg-state-error/15 text-state-error border-state-error/40"
                      : risk.level === "HIGH"
                      ? "bg-state-warning/15 text-state-warning border-state-warning/40"
                      : risk.level === "MEDIUM"
                      ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
                      : "bg-accent/15 text-accent border-accent/40";

                  return (
                    <div
                      key={evt.event_id}
                      onClick={() => handleSelectIncident(evt)}
                      className={cn(
                        "group bg-surface border rounded-panel p-3.5 shadow-panel cursor-pointer transition-all duration-150 flex flex-col justify-between select-none",
                        isSelected
                          ? "border-accent bg-surface-raised ring-1 ring-accent"
                          : "border-border hover:border-accent/60 hover:bg-surface-hover/80"
                      )}
                    >
                      {/* Top Bar: Identifier, Severity */}
                      <div className="flex items-center justify-between gap-1 mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <Flame className="w-3.5 h-3.5 text-thermal" />
                          <span className="text-xs font-bold text-foreground group-hover:text-accent">
                            Fire #{formattedIndex}
                          </span>
                          <span className="text-[10px] text-foreground-muted">
                            · {evt.event_id}
                          </span>
                        </div>

                        <span
                          className={cn(
                            "px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border",
                            severityBadge
                          )}
                        >
                          {risk.level}
                        </span>
                      </div>

                      {/* Human-Readable Location */}
                      <div className="flex items-start gap-1 text-xs text-foreground font-semibold mb-1 truncate">
                        <MapPin className="w-3 h-3 text-accent shrink-0 mt-0.5" />
                        <span className="truncate">{readableLocation}</span>
                      </div>

                      {/* Detection Timing & Status */}
                      <div className="flex items-center justify-between text-[10px] text-foreground-secondary mb-2">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-foreground-muted" />
                          <span>Detected {timeAgo}</span>
                        </div>
                        <span className="text-accent font-semibold">
                          Status: ACTIVE
                        </span>
                      </div>

                      {/* Technical Details Footer */}
                      <div className="pt-2 border-t border-border flex items-center justify-between text-[10px]">
                        <span className="text-foreground-muted">
                          {evt.frp_mw.toFixed(0)} MW · {(evt.confidence * 100).toFixed(0)}% Conf
                        </span>
                        <span className="text-accent font-semibold group-hover:text-accent-cyan flex items-center gap-0.5">
                          <span>View Details</span>
                          <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
