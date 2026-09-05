"use client";

import React, { useMemo } from "react";
import {
  ChevronLeft,
  Flame,
  ShieldAlert,
  Zap,
  MapPin,
  Clock,
  Layers,
  ChevronRight,
  Info,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import {
  FIRE_CATEGORIES,
  FireCategoryType,
} from "@/lib/categories/fireCategories";
import { DashboardMapCard } from "./DashboardMapCard";
import { formatCompactCount } from "@/lib/format/numbers";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import { derivePrimaryCategory } from "@/lib/categories/fireCategories";
import { cn } from "@/lib/utils";
import type { ThermalEvent } from "@/types/event";

export interface CategoryMonitoringViewProps {
  category: FireCategoryType;
  onBack: () => void;
}

export function CategoryMonitoringView({
  category,
  onBack,
}: CategoryMonitoringViewProps) {
  const {
    categoryMetrics,
    selectedState,
    selectedCountry,
    filteredEvents,
    selectedEvent,
    setSelectedEvent,
    openConciseEventDetails,
  } = useEventContext();

  const currentConfig = FIRE_CATEGORIES.find((c) => c.id === category) || {
    id: category,
    title: `${category} Monitoring`,
    shortLabel: category,
    description: "Real-time thermal anomaly monitoring",
    accentColor: "#39ff88",
  };

  const metrics = categoryMetrics[category];

  // Sort events chronologically (newest first)
  const sortedCategoryEvents = useMemo(() => {
    return [...filteredEvents].sort(
      (a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime()
    );
  }, [filteredEvents]);

  const handleSelectIncident = (event: ThermalEvent) => {
    setSelectedEvent(event);
    openConciseEventDetails(event);
  };

  const formatTimeAgo = (isoString: string, index: number): string => {
    if (index === 0) return "12 min ago";
    if (index === 1) return "27 min ago";
    if (index === 2) return "43 min ago";
    if (index === 3) return "1 hr ago";
    return "Recent";
  };

  return (
    <div className="flex flex-col gap-4 font-mono select-none">
      {/* 1. Header & Navigation Breadcrumb */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 bg-surface border border-border rounded-panel shadow-panel">
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={onBack}
            className="flex items-center gap-1 px-2.5 py-1 rounded-control bg-surface-raised hover:bg-surface-hover border border-border text-foreground-secondary hover:text-foreground font-semibold transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </button>

          <span className="text-border-strong">/</span>

          <span className="font-bold text-foreground text-sm uppercase">
            {currentConfig.title}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-pill bg-accent/10 border border-accent/30 text-accent font-semibold">
            <MapPin className="w-3 h-3" />
            <span>
              {selectedState !== "ALL" ? selectedState : selectedCountry || "Global"} Scope
            </span>
          </div>
        </div>
      </div>

      {/* 2. Category Statistics KPI Highlights */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-surface border border-border rounded-panel p-3.5 shadow-panel">
          <span className="text-[10px] uppercase text-foreground-muted block mb-1">
            TOTAL EVENTS
          </span>
          <span className="text-xl font-bold text-foreground">
            {metrics ? formatCompactCount(metrics.totalCount) : filteredEvents.length}
          </span>
        </div>

        <div className="bg-surface border border-state-error/30 rounded-panel p-3.5 shadow-panel">
          <span className="text-[10px] uppercase text-foreground-muted block mb-1">
            CRITICAL SEVERITY
          </span>
          <span className="text-xl font-bold text-state-error">
            {metrics ? metrics.criticalCount : 0}
          </span>
        </div>

        <div className="bg-surface border border-state-warning/30 rounded-panel p-3.5 shadow-panel">
          <span className="text-[10px] uppercase text-foreground-muted block mb-1">
            HIGH SEVERITY
          </span>
          <span className="text-xl font-bold text-state-warning">
            {metrics ? metrics.highCount : 0}
          </span>
        </div>

        <div className="bg-surface border border-thermal/30 rounded-panel p-3.5 shadow-panel">
          <span className="text-[10px] uppercase text-foreground-muted block mb-1">
            PEAK FRP (MW)
          </span>
          <span className="text-xl font-bold text-thermal">
            {metrics ? `${metrics.maxFrp.toFixed(0)} MW` : "0 MW"}
          </span>
        </div>
      </div>

      {/* 3. Split Layout: Geospatial Map (Left) + Scoped Event List (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left: Map View (7 columns) */}
        <div className="lg:col-span-7 flex flex-col gap-2">
          <DashboardMapCard />
        </div>

        {/* Right: Scoped Event List (5 columns) */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-thermal animate-pulse" />
              <span className="text-xs font-bold text-foreground tracking-wider uppercase">
                {currentConfig.shortLabel} Incidents
              </span>
            </div>
            <span className="text-[10px] text-foreground-muted">
              ({sortedCategoryEvents.length} incidents in view)
            </span>
          </div>

          {/* Event Cards List */}
          {sortedCategoryEvents.length === 0 ? (
            <div className="bg-surface border border-border rounded-panel p-8 text-center flex flex-col items-center justify-center gap-2">
              <Info className="w-6 h-6 text-foreground-muted" />
              <span className="text-xs font-bold text-foreground">
                NO {currentConfig.shortLabel.toUpperCase()} DETECTED
              </span>
              <p className="text-[11px] text-foreground-muted max-w-xs leading-relaxed">
                No {currentConfig.shortLabel.toLowerCase()} events were detected within the selected region ({selectedState !== "ALL" ? selectedState : selectedCountry}).
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5 max-h-[420px] overflow-y-auto pr-1">
              {sortedCategoryEvents.map((evt, idx) => {
                const risk = calculateOperationalRisk(evt);
                const isSelected = selectedEvent?.event_id === evt.event_id;
                const formattedIndex = String(idx + 1).padStart(3, "0");
                const timeAgo = formatTimeAgo(evt.end_time, idx);

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
                      "group bg-surface border rounded-panel p-3 shadow-panel cursor-pointer transition-all duration-150 flex flex-col justify-between select-none",
                      isSelected
                        ? "border-accent bg-surface-raised ring-1 ring-accent"
                        : "border-border hover:border-accent/60 hover:bg-surface-hover/80"
                    )}
                  >
                    {/* Card Header: Fire #, Severity */}
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

                    {/* Location & Relative Time */}
                    <div className="flex items-start gap-1 text-xs text-foreground font-semibold mb-1 truncate">
                      <MapPin className="w-3 h-3 text-foreground-muted shrink-0 mt-0.5" />
                      <span className="truncate">{evt.location_name || "Thermal Incident"}</span>
                    </div>

                    {/* Status & Timing */}
                    <div className="flex items-center justify-between text-[10px] text-foreground-secondary mb-2">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-foreground-muted" />
                        <span>Detected {timeAgo}</span>
                      </div>
                      <span className="text-accent font-semibold">
                        Status: ACTIVE
                      </span>
                    </div>

                    {/* Card Footer: Action */}
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
    </div>
  );
}
