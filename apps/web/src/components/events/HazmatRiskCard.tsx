"use client";

import React from "react";
import { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import { AlertTriangle, ShieldAlert, Biohazard, Flame } from "lucide-react";
import { cn } from "@/lib/utils";

export interface HazmatRiskCardProps {
  event: ThermalEvent;
  evidence?: EventEvidenceResponse | null;
  className?: string;
}

export function HazmatRiskCard({
  event,
  evidence,
  className,
}: HazmatRiskCardProps) {
  const isIndustrial = event.classification === "INDUSTRIAL";
  const facilityName = evidence?.facility_name || "Petrochemical & Refining Complex";

  // Derive CAMEO-NIOSH hazmat metrics based on classification
  const unCodes = isIndustrial ? ["UN1267", "UN1114", "UN1075"] : ["UN1361"];
  const isoDist = isIndustrial ? 800 : 300;
  const downwindDay = isIndustrial ? 1600 : 800;
  const downwindNight = isIndustrial ? 2400 : 1200;
  const chemicals = isIndustrial
    ? "Crude Oil, Benzene, LPG, Hydrogen Sulfide (H2S)"
    : "Biomass Volatiles, Carbon Monoxide, PM2.5";
  const protocol = isIndustrial
    ? "AFFF Alcohol-Resistant Foam & High-Volume Deluge"
    : "Water Fog Line & Forest Firebreak Containment";

  return (
    <div
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5",
        className
      )}
    >
      {/* 1. Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5 text-foreground">
          <Biohazard className="w-3.5 h-3.5 text-state-warning" />
          <span className="text-[11px] font-bold tracking-wider uppercase">
            CAMEO-NIOSH Chemical Hazards
          </span>
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-state-warning/10 border border-state-warning/30 text-state-warning font-semibold">
          ERG 2024
        </span>
      </div>

      {/* 2. Facility & Primary Chemicals */}
      <div className="space-y-1 text-[10px]">
        <div className="flex items-center justify-between">
          <span className="text-foreground-muted">FACILITY SECTOR:</span>
          <span className="text-foreground font-semibold truncate max-w-[180px]">
            {isIndustrial ? "Petroleum Refining" : "Vegetation / Forest Sector"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-foreground-muted">UN/NA CODES:</span>
          <span className="text-accent font-semibold">{unCodes.join(", ")}</span>
        </div>
        <div className="text-[9px] text-foreground-secondary bg-background/50 p-1.5 rounded border border-border/40 mt-1">
          <span className="text-foreground font-semibold">Chemicals: </span>
          {chemicals}
        </div>
      </div>

      {/* 3. Emergency Isolation Distances */}
      <div className="grid grid-cols-3 gap-1.5 text-[9px] text-center">
        <div className="p-1 rounded bg-state-error/10 border border-state-error/30">
          <div className="text-state-error font-semibold text-[8px]">INITIAL ISOLATION</div>
          <div className="font-bold text-foreground mt-0.5">{isoDist}m</div>
        </div>
        <div className="p-1 rounded bg-state-warning/10 border border-state-warning/30">
          <div className="text-state-warning font-semibold text-[8px]">DOWNWIND (DAY)</div>
          <div className="font-bold text-foreground mt-0.5">{downwindDay}m</div>
        </div>
        <div className="p-1 rounded bg-state-warning/10 border border-state-warning/30">
          <div className="text-state-warning font-semibold text-[8px]">DOWNWIND (NIGHT)</div>
          <div className="font-bold text-foreground mt-0.5">{downwindNight}m</div>
        </div>
      </div>

      {/* 4. Firefighting Directive */}
      <div className="pt-1 border-t border-border/40 text-[8.5px] text-foreground-muted flex items-start gap-1">
        <ShieldAlert className="w-3 h-3 text-accent shrink-0 mt-0.5" />
        <span>
          <strong className="text-foreground">Protocol:</strong> {protocol}
        </span>
      </div>
    </div>
  );
}
