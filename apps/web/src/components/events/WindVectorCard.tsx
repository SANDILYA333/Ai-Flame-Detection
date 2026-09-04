"use client";

import React from "react";
import type { WindVector, DataQuality } from "@/types/weather";
import { Wind, Compass, AlertTriangle, CheckCircle2, ShieldAlert, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface WindVectorCardProps {
  wind?: WindVector | null;
  dataQuality?: DataQuality;
  providerName?: string;
  isLoading?: boolean;
  className?: string;
}

export function WindVectorCard({
  wind,
  dataQuality = "LIVE",
  providerName = "Open-Meteo",
  isLoading = false,
  className,
}: WindVectorCardProps) {
  if (isLoading) {
    return (
      <div className={cn("p-3 rounded-control bg-surface/90 border border-border/80 font-mono animate-pulse space-y-2", className)}>
        <div className="h-3 w-32 bg-surface-hover rounded" />
        <div className="h-8 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  if (!wind) {
    return (
      <div className={cn("p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-1.5", className)}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Wind className="w-3.5 h-3.5 text-accent-cyan" />
            Atmospheric Conditions
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-hover text-foreground-muted border border-border">
            UNAVAILABLE
          </span>
        </div>
        <p className="text-[10px] text-foreground-muted">
          Real-time meteorological observations temporarily unavailable for coordinates.
        </p>
      </div>
    );
  }

  const speedKmh = Number((wind.speed_ms * 3.6).toFixed(1));
  const gustKmh = wind.gust_ms ? Number((wind.gust_ms * 3.6).toFixed(1)) : null;
  const isCalm = wind.is_calm || wind.speed_ms < 0.5;

  const qualityBadgeClass =
    dataQuality === "LIVE"
      ? "bg-state-success/15 text-state-success border-state-success/30"
      : dataQuality === "CACHED"
      ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/30"
      : dataQuality === "FALLBACK"
      ? "bg-state-warning/15 text-state-warning border-state-warning/30"
      : "bg-surface-hover text-foreground-muted border-border";

  return (
    <div
      data-testid="wind-vector-card"
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5 shadow-sm transition-all",
        className
      )}
    >
      {/* 1. Header & Data Provenance */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5">
          <Wind className="w-3.5 h-3.5 text-accent-cyan" />
          <span className="text-[11px] font-bold text-foreground tracking-wider uppercase">
            ATMOSPHERIC WIND VECTOR
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={cn("text-[9px] px-1.5 py-0.2 rounded border font-bold uppercase", qualityBadgeClass)}>
            {dataQuality}
          </span>
          <span className="text-[9px] text-foreground-muted">{providerName}</span>
        </div>
      </div>

      {/* 2. Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 bg-background/80 p-2 rounded-control border border-border/60 text-[10px]">
        {/* Wind Speed */}
        <div>
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
            Wind Velocity
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="font-bold text-foreground text-sm">{wind.speed_ms.toFixed(1)}</span>
            <span className="text-foreground-muted text-[10px]">m/s</span>
            <span className="text-foreground-secondary text-[10px] ml-1">({speedKmh} km/h)</span>
          </div>
          {gustKmh && (
            <div className="text-[9px] text-foreground-muted mt-0.5">
              Gusts: <span className="text-foreground">{gustKmh} km/h</span>
            </div>
          )}
        </div>

        {/* Intensity State */}
        <div>
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
            Intensity State
          </span>
          <div className="mt-1">
            <span
              className={cn(
                "font-bold text-[10px] px-1.5 py-0.5 rounded border uppercase",
                isCalm
                  ? "bg-state-warning/15 text-state-warning border-state-warning/30"
                  : wind.wind_state === "STRONG" || wind.wind_state === "GALE"
                  ? "bg-state-error/15 text-state-error border-state-error/30"
                  : "bg-accent/15 text-accent border-accent/30"
              )}
            >
              {wind.wind_state || (isCalm ? "CALM" : "MODERATE")}
            </span>
          </div>
        </div>

        {/* Wind Origin (FROM) */}
        <div className="pt-1.5 border-t border-border/40">
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider flex items-center gap-1">
            <Compass className="w-2.5 h-2.5 text-accent" />
            Wind FROM
          </span>
          <span className="font-bold text-foreground text-xs mt-0.5 block">
            {wind.direction_from_label} ({wind.direction_from_deg.toFixed(0)}°)
          </span>
        </div>

        {/* Downwind Transport (TO) */}
        <div className="pt-1.5 border-t border-border/40">
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider flex items-center gap-1">
            <ArrowUpRight className="w-2.5 h-2.5 text-state-error" />
            Downwind TO
          </span>
          <span className="font-bold text-state-error text-xs mt-0.5 block">
            {wind.downwind_direction_label} ({wind.direction_to_deg.toFixed(0)}°)
          </span>
        </div>
      </div>

      {/* 3. Stagnation / Low-Wind Advisory */}
      {isCalm && (
        <div className="p-2 rounded bg-state-warning/10 border border-state-warning/30 text-[10px] text-state-warning flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <p className="leading-tight">
            <strong>Atmospheric Stagnation:</strong> Low wind speed (&lt;0.5 m/s) leads to lateral dispersion broadening and local hazard accumulation.
          </p>
        </div>
      )}
    </div>
  );
}
