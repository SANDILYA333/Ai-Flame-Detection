"use client";

import React from "react";
import { Flame, Clock, AlertTriangle, MapPin, Zap, ArrowUpRight } from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { formatCompactCount } from "@/lib/format/numbers";

export function DashboardStatsGrid() {
  const { stats, selectedState, activeMetricFilter, handleMetricCardClick } = useEventContext();

  const cards = [
    {
      id: "active-fires",
      label: "ACTIVE FIRES",
      value: stats.total,
      subtext: selectedState !== "ALL" ? `In ${selectedState}` : "In Selected Scope",
      actionHint: "View active events",
      icon: Flame,
      color: "text-thermal",
      bgColor: "bg-thermal/10",
      borderColor: "border-thermal/30",
      activeRing: "ring-2 ring-thermal",
      isActive: activeMetricFilter === "ACTIVE_FIRES",
    },
    {
      id: "detected-today",
      label: "DETECTED TODAY",
      value: stats.detectedToday,
      subtext: "Last 24 Hours",
      actionHint: "View recent 24h",
      icon: Clock,
      color: "text-accent-cyan",
      bgColor: "bg-accent-cyan/10",
      borderColor: "border-accent-cyan/30",
      activeRing: "ring-2 ring-accent-cyan",
      isActive: activeMetricFilter === "DETECTED_TODAY",
    },
    {
      id: "high-severity",
      label: "HIGH / CRITICAL",
      value: stats.critical + stats.high,
      subtext: `${stats.critical} Critical · ${stats.high} High`,
      actionHint: "View high & critical",
      icon: AlertTriangle,
      color: "text-state-error",
      bgColor: "bg-state-error/10",
      borderColor: "border-state-error/30",
      activeRing: "ring-2 ring-state-error",
      isActive: activeMetricFilter === "HIGH_CRITICAL",
    },
    {
      id: "regions-affected",
      label: "REGIONS AFFECTED",
      value: stats.affectedRegionsCount,
      subtext: selectedState !== "ALL" ? `${selectedState} Districts` : "Active Locations",
      actionHint: "View affected regions",
      icon: MapPin,
      color: "text-accent",
      bgColor: "bg-accent/10",
      borderColor: "border-accent/30",
      activeRing: "ring-2 ring-accent",
      isActive: activeMetricFilter === "REGIONS_AFFECTED",
    },
    {
      id: "max-frp",
      label: "PEAK INTENSITY",
      value: `${stats.maxFrp.toFixed(0)} MW`,
      subtext: "Fire Radiative Power",
      actionHint: "Inspect peak event",
      icon: Zap,
      color: "text-state-warning",
      bgColor: "bg-state-warning/10",
      borderColor: "border-state-warning/30",
      activeRing: "ring-2 ring-state-warning",
      isActive: false,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 font-mono">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <button
            key={card.id}
            type="button"
            onClick={() => handleMetricCardClick(card.id)}
            className={`group text-left relative bg-surface border ${card.borderColor} rounded-panel p-3.5 shadow-panel flex flex-col justify-between transition-all duration-200 hover:bg-surface-raised hover:border-border-strong hover:scale-[1.01] cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent ${
              card.isActive ? `${card.activeRing} bg-surface-raised` : ""
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-2 w-full">
              <span className="text-[10px] uppercase tracking-wider text-foreground-muted group-hover:text-foreground transition-colors">
                {card.label}
              </span>
              <div className="flex items-center gap-1.5">
                <ArrowUpRight className="w-3 h-3 text-foreground-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                <div
                  className={`w-7 h-7 rounded-control ${card.bgColor} flex items-center justify-center ${card.color}`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>

            <div className="flex flex-col">
              <span className={`text-2xl font-bold tracking-tight ${card.color} leading-none mb-1`}>
                {typeof card.value === "number" ? formatCompactCount(card.value) : card.value}
              </span>
              <div className="flex items-center justify-between gap-1">
                <span className="text-[10px] text-foreground-muted truncate">
                  {card.subtext}
                </span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
