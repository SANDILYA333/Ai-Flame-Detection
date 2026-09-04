"use client";

import React from "react";
import type { AtmosphericDispersionResult } from "@/types/dispersion";
import { Activity, AlertCircle, Info, Layers, ShieldAlert, Sparkles, Navigation } from "lucide-react";
import { cn } from "@/lib/utils";

export interface HazardDispersionCardProps {
  dispersion?: AtmosphericDispersionResult | null;
  isLoading?: boolean;
  className?: string;
}

export function HazardDispersionCard({
  dispersion,
  isLoading = false,
  className,
}: HazardDispersionCardProps) {
  if (isLoading) {
    return (
      <div className={cn("p-3 rounded-control bg-surface/90 border border-border/80 font-mono animate-pulse space-y-2", className)}>
        <div className="h-3 w-40 bg-surface-hover rounded" />
        <div className="h-10 w-full bg-surface-hover rounded" />
      </div>
    );
  }

  if (!dispersion || !dispersion.dispersion) {
    return null;
  }

  const { dispersion: summary, trajectory, wind, model_confidence } = dispersion;

  const stabilityClassColors: Record<string, string> = {
    A: "bg-state-error/20 text-state-error border-state-error/40",
    B: "bg-accent/20 text-accent border-accent/40",
    C: "bg-state-warning/20 text-state-warning border-state-warning/40",
    D: "bg-accent-cyan/20 text-accent-cyan border-accent-cyan/40",
    E: "bg-state-success/20 text-state-success border-state-success/40",
    F: "bg-foreground-muted/20 text-foreground-muted border-foreground-muted/40",
  };

  const stabilityBadge = stabilityClassColors[summary.stability_class] || stabilityClassColors.D;

  return (
    <div
      data-testid="hazard-dispersion-card"
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5 shadow-sm transition-all",
        className
      )}
    >
      {/* 1. Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <span className="text-[11px] font-bold text-foreground tracking-wider uppercase">
            GAUSSIAN DISPERSION PLUME
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-foreground-muted uppercase tracking-wider">Pasquill</span>
          <span className={cn("text-[9px] px-1.5 py-0.2 rounded border font-bold uppercase", stabilityBadge)}>
            Class {summary.stability_class}
          </span>
        </div>
      </div>

      {/* 2. Physical Characteristics Grid */}
      <div className="grid grid-cols-2 gap-2 bg-background/80 p-2 rounded-control border border-border/60 text-[10px]">
        <div>
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
            Downwind Hazard Reach
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="font-bold text-foreground text-xs">{summary.max_hazard_distance_km.toFixed(1)}</span>
            <span className="text-foreground-muted text-[10px]">km</span>
          </div>
        </div>

        <div>
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
            Max Lateral Width
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="font-bold text-foreground text-xs">{summary.max_hazard_width_km.toFixed(2)}</span>
            <span className="text-foreground-muted text-[10px]">km</span>
          </div>
        </div>

        <div className="pt-1.5 border-t border-border/40">
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider flex items-center gap-1">
            <Navigation className="w-2.5 h-2.5 text-accent" />
            Plume Bearing
          </span>
          <span className="font-bold text-foreground text-[10.5px] mt-0.5 block">
            {summary.plume_angle_deg.toFixed(0)}° ({wind.downwind_direction_label})
          </span>
        </div>

        <div className="pt-1.5 border-t border-border/40">
          <span className="text-foreground-muted block text-[9px] uppercase tracking-wider">
            Effective Release H
          </span>
          <span className="font-bold text-foreground text-[10.5px] mt-0.5 block">
            {summary.effective_release_height_m.toFixed(1)} m
          </span>
        </div>
      </div>

      {/* 3. Atmospheric Stability Rationale */}
      <div className="text-[10px] text-foreground-secondary bg-surface-hover/50 p-2 rounded border border-border/40 leading-relaxed">
        <span className="text-foreground-muted block text-[9px] uppercase tracking-wider font-bold mb-0.5">
          Atmospheric Stability Rationale:
        </span>
        {summary.stability_rationale}
      </div>

      {/* 4. Cross-Section Concentration Step Progression */}
      {trajectory && trajectory.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[9px] text-foreground-muted font-bold uppercase tracking-wider">
            <span>Downwind Hazard Gradient</span>
            <span>Peak Touchdown → Dissipation</span>
          </div>
          <div className="grid grid-cols-6 gap-1 h-2">
            {trajectory.slice(0, 6).map((pt, idx) => (
              <div
                key={idx}
                title={`Distance: ${pt.downwind_distance_km}km, Rel Conc: ${pt.relative_concentration.toFixed(2)}`}
                className={cn(
                  "rounded-xs h-full transition-all",
                  pt.relative_concentration > 0.7
                    ? "bg-state-error"
                    : pt.relative_concentration > 0.4
                    ? "bg-accent"
                    : pt.relative_concentration > 0.1
                    ? "bg-state-warning"
                    : "bg-surface-hover"
                )}
                style={{ opacity: Math.max(0.2, pt.relative_concentration) }}
              />
            ))}
          </div>
        </div>
      )}

      {/* 5. Engineering Approximation Notice */}
      <div className="flex items-center gap-1.5 text-[9px] font-mono text-foreground-muted pt-1 border-t border-border/40">
        <Info className="w-3 h-3 text-accent shrink-0" />
        <span className="leading-tight">
          Modeled Gaussian plume estimate for situational awareness & hazard bounding.
        </span>
      </div>
    </div>
  );
}
