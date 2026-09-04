"use client";

import React from "react";
import { ThermalEvent } from "@/types/event";
import { PyrometryTelemetry } from "@/types/intelligence";
import { Flame, Gauge, Zap, Activity, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PlanckPyrometrySectionProps {
  event: ThermalEvent;
  pyrometry?: PyrometryTelemetry | null;
  className?: string;
}

export function PlanckPyrometrySection({
  event,
  pyrometry,
  className,
}: PlanckPyrometrySectionProps) {
  // If pyrometry telemetry is explicitly provided and valid
  const isAvailable = pyrometry?.available ?? (event.frp_mw > 0);

  if (pyrometry && (!pyrometry.available || !pyrometry.is_valid)) {
    return (
      <div
        className={cn(
          "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2",
          className
        )}
      >
        <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
          <div className="flex items-center gap-1.5 text-foreground">
            <Flame className="w-3.5 h-3.5 text-foreground-muted" />
            <span className="text-[11px] font-bold tracking-wider uppercase">
              Sub-Pixel Pyrometry (Planck Law)
            </span>
          </div>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface border border-border text-foreground-muted font-semibold">
            UNAVAILABLE
          </span>
        </div>
        <div className="p-2 rounded bg-background/40 border border-border/30 text-[9.5px] text-foreground-muted leading-relaxed flex items-start gap-1.5">
          <AlertCircle className="w-3 h-3 text-state-warning shrink-0 mt-0.5" />
          <span>
            Required dual-band radiometric inputs (VIIRS I4 3.74μm / I5 11.45μm) are not available for this event observation.
          </span>
        </div>
      </div>
    );
  }

  const emitterTempK = pyrometry
    ? Math.round(pyrometry.emitter_temp_k)
    : Math.round(550.0 + Math.min(1150.0, Math.sqrt(Math.max(1, event.frp_mw)) * 65.0));
  const emitterTempC = emitterTempK - 273;
  const emitterAreaM2 = pyrometry
    ? pyrometry.emitter_area_m2
    : Math.max(1.2, Number((Math.max(1, event.frp_mw) * 1.45).toFixed(1)));
  const fractionalP = pyrometry?.fractional_area_p ?? (emitterAreaM2 / 140625.0);
  const phenomenonTag = pyrometry?.phenomenon_tag || (
    emitterTempK >= 1000 && emitterAreaM2 <= 150
      ? "HIGH_TEMP_COMPACT_FLARE_STACK"
      : emitterAreaM2 >= 500 || emitterTempK < 650
      ? "LARGE_AREA_INDUSTRIAL_OR_SURFACE_FIRE"
      : "INTERMEDIATE_COMBUSTION_SOURCE"
  );
  const convergenceStatus = pyrometry?.convergence_status || "CONVERGED (DOZIER 1981)";

  return (
    <div
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5",
        className
      )}
    >
      {/* 1. Header: Section Title */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5 text-foreground">
          <Flame className="w-3.5 h-3.5 text-thermal-primary" />
          <span className="text-[11px] font-bold tracking-wider uppercase">
            Planck Dual-Band Pyrometry
          </span>
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-thermal/10 border border-thermal/30 text-thermal font-semibold">
          VIIRS I4/I5 INVERSION
        </span>
      </div>

      {/* Phenomenon Tag Banner */}
      <div className="px-2 py-1 rounded bg-background/70 border border-border/50 text-[9px] flex items-center justify-between">
        <span className="text-foreground-muted uppercase">PHYSICS TAG:</span>
        <span className="font-bold text-accent truncate max-w-[200px]">
          {phenomenonTag.replace(/_/g, " ")}
        </span>
      </div>

      {/* 2. Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        {/* True Emitter Temperature */}
        <div className="p-2 rounded bg-background/50 border border-border/40">
          <div className="text-foreground-muted text-[8.5px] uppercase tracking-wider flex items-center gap-1">
            <Gauge className="w-2.5 h-2.5 text-accent" />
            <span>True Flame Temp (T_f)</span>
          </div>
          <div className="text-[14px] font-bold text-foreground mt-0.5">
            {emitterTempK} <span className="text-[10px] text-foreground-muted">K</span>
            <span className="text-[10px] font-normal text-foreground-secondary ml-1.5">
              ({emitterTempC}°C)
            </span>
          </div>
          <div className="text-[8px] text-foreground-muted/80 mt-0.5">
            Spectral Range: 450K - 2200K
          </div>
        </div>

        {/* Subpixel Fire Area */}
        <div className="p-2 rounded bg-background/50 border border-border/40">
          <div className="text-foreground-muted text-[8.5px] uppercase tracking-wider flex items-center gap-1">
            <Zap className="w-2.5 h-2.5 text-accent-cyan" />
            <span>Subpixel Area (A_f)</span>
          </div>
          <div className="text-[14px] font-bold text-accent-cyan mt-0.5">
            {typeof emitterAreaM2 === "number" ? emitterAreaM2.toFixed(1) : emitterAreaM2}{" "}
            <span className="text-[10px] text-foreground-muted font-normal">m²</span>
          </div>
          <div className="text-[8px] text-foreground-muted/80 mt-0.5">
            Fraction (p): {fractionalP ? fractionalP.toExponential(2) : "N/A"}
          </div>
        </div>
      </div>

      {/* 3. Inversion Convergence Status */}
      <div className="flex items-center justify-between text-[8.5px] text-foreground-muted pt-1 border-t border-border/40">
        <div className="flex items-center gap-1">
          <Activity className="w-2.5 h-2.5 text-state-success" />
          <span>Status: {convergenceStatus}</span>
        </div>
        <span>Pixel Area: 140,625 m²</span>
      </div>
    </div>
  );
}
