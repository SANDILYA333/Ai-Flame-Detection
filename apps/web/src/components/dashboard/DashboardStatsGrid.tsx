"use client";

import React from "react";
import { Flame, Clock, AlertTriangle, MapPin, Zap } from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { formatCompactCount } from "@/lib/format/numbers";

export function DashboardStatsGrid() {
  const { stats, selectedState } = useEventContext();

  const cards = [
    {
      id: "active-fires",
      label: "ACTIVE FIRES",
      value: stats.total,
      subtext: selectedState !== "ALL" ? `In ${selectedState}` : "In Selected Scope",
      icon: Flame,
      color: "text-thermal",
      bgColor: "bg-thermal/10",
      borderColor: "border-thermal/30",
      glow: "glow-thermal",
    },
    {
      id: "detected-today",
      label: "DETECTED TODAY",
      value: stats.detectedToday,
      subtext: "Last 24 Hours",
      icon: Clock,
      color: "text-accent-cyan",
      bgColor: "bg-accent-cyan/10",
      borderColor: "border-accent-cyan/30",
      glow: "",
    },
    {
      id: "high-severity",
      label: "HIGH / CRITICAL",
      value: stats.critical + stats.high,
      subtext: `${stats.critical} Critical · ${stats.high} High`,
      icon: AlertTriangle,
      color: "text-state-error",
      bgColor: "bg-state-error/10",
      borderColor: "border-state-error/30",
      glow: "",
    },
    {
      id: "regions-affected",
      label: "REGIONS AFFECTED",
      value: stats.affectedRegionsCount,
      subtext: selectedState !== "ALL" ? `${selectedState} Districts` : "Active Locations",
      icon: MapPin,
      color: "text-accent",
      bgColor: "bg-accent/10",
      borderColor: "border-accent/30",
      glow: "",
    },
    {
      id: "max-frp",
      label: "PEAK INTENSITY",
      value: `${stats.maxFrp.toFixed(0)} MW`,
      subtext: "Fire Radiative Power",
      icon: Zap,
      color: "text-state-warning",
      bgColor: "bg-state-warning/10",
      borderColor: "border-state-warning/30",
      glow: "",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 font-mono">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.id}
            className={`bg-surface border ${card.borderColor} rounded-panel p-3.5 shadow-panel flex flex-col justify-between transition-all hover:bg-surface-raised`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[10px] uppercase tracking-wider text-foreground-muted">
                {card.label}
              </span>
              <div
                className={`w-7 h-7 rounded-control ${card.bgColor} flex items-center justify-center ${card.color}`}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>
            </div>

            <div className="flex flex-col">
              <span className={`text-2xl font-bold tracking-tight ${card.color} leading-none mb-1`}>
                {typeof card.value === "number" ? formatCompactCount(card.value) : card.value}
              </span>
              <span className="text-[10px] text-foreground-muted truncate">
                {card.subtext}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
