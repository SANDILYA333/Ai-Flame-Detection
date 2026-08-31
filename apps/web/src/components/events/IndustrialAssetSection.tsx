"use client";

import React, { useMemo } from "react";
import { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import { resolveIndustrialAssets } from "@/lib/assets/resolver";
import type { AssetType } from "@/types/asset";
import {
  Building2,
  Factory,
  Zap,
  Layers,
  Database,
  GitCommit,
  Trees,
  Info,
  MapPin,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

export interface IndustrialAssetSectionProps {
  event: ThermalEvent;
  evidence?: EventEvidenceResponse | null;
  className?: string;
}

function getAssetIcon(type: AssetType) {
  switch (type) {
    case "REFINERY":
    case "PETROCHEMICAL":
    case "METALLURGICAL":
    case "INDUSTRIAL_ZONE":
      return <Factory className="w-3.5 h-3.5 text-accent" />;
    case "POWER_PLANT":
      return <Zap className="w-3.5 h-3.5 text-state-warning" />;
    case "STORAGE_FACILITY":
      return <Database className="w-3.5 h-3.5 text-accent-cyan" />;
    case "PIPELINE":
      return <GitCommit className="w-3.5 h-3.5 text-foreground-secondary" />;
    case "AGRICULTURAL_PARCEL":
      return <Trees className="w-3.5 h-3.5 text-state-success" />;
    case "OTHER":
    default:
      return <Building2 className="w-3.5 h-3.5 text-foreground-muted" />;
  }
}

export function IndustrialAssetSection({
  event,
  evidence,
  className,
}: IndustrialAssetSectionProps) {
  const contextData = useMemo(
    () => resolveIndustrialAssets(event, evidence),
    [event, evidence]
  );

  return (
    <div
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5",
        className
      )}
    >
      {/* 1. Header: Section Title & Exposure Level Badge */}
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div className="flex items-center gap-1.5 text-foreground">
          <Building2 className="w-3.5 h-3.5 text-accent-cyan" />
          <span className="text-[11px] font-bold tracking-wider uppercase">
            Industrial Context & Assets
          </span>
        </div>

        <span
          className={cn(
            "text-[9px] px-2 py-0.5 rounded border font-bold font-mono uppercase",
            contextData.overallExposure === "HIGH"
              ? "bg-accent/15 border-accent/40 text-accent"
              : contextData.overallExposure === "MEDIUM"
              ? "bg-state-warning/15 border-state-warning/40 text-state-warning"
              : contextData.overallExposure === "LOW"
              ? "bg-state-success/15 border-state-success/40 text-state-success"
              : "bg-surface border-border text-foreground-muted"
          )}
        >
          {contextData.overallExposure === "NO_ASSETS_DETECTED"
            ? "NO PROXIMATE ASSETS"
            : `EXPOSURE: ${contextData.overallExposure}`}
        </span>
      </div>

      {/* 2. Asset List or Graceful Empty State */}
      {contextData.hasAssetData ? (
        <div className="space-y-1.5">
          <div className="text-[9px] uppercase tracking-wider text-foreground-muted font-semibold">
            Nearby Infrastructure ({contextData.assets.length} Detected)
          </div>

          <div className="space-y-1 text-[10px]">
            {contextData.assets.map((asset) => (
              <div
                key={asset.id}
                className="p-2 rounded bg-background/60 border border-border/50 flex items-start justify-between gap-2"
              >
                <div className="flex items-start gap-2 min-w-0">
                  <div className="shrink-0 mt-0.5">{getAssetIcon(asset.type)}</div>
                  <div className="min-w-0">
                    <div className="font-semibold text-foreground truncate">{asset.name}</div>
                    <div className="text-[9px] text-foreground-muted flex items-center gap-1.5 mt-0.5">
                      <span className="px-1 py-0.2 rounded bg-surface border border-border/60 text-foreground-secondary">
                        {asset.type.replace(/_/g, " ")}
                      </span>
                      <span>·</span>
                      <span className="truncate">{asset.sourceType}</span>
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="font-bold text-accent font-mono">
                    {asset.formattedDistance}
                  </div>
                  <div className="text-[8.5px] text-foreground-muted uppercase">
                    Geodesic Dist
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-3 rounded-control border border-dashed border-border/80 bg-background/30 text-center space-y-1">
          <Building2 className="w-5 h-5 text-foreground-muted mx-auto" />
          <div className="text-[11px] font-semibold text-foreground">
            No Asset Intelligence Available
          </div>
          <div className="text-[9.5px] text-foreground-muted max-w-[220px] mx-auto">
            No mapped heavy industrial infrastructure detected within analysis perimeter.
          </div>
        </div>
      )}

      {/* 3. Scientific Invariant Context Notice */}
      <div className="pt-1.5 border-t border-border/50 flex items-start gap-1 text-[8.5px] text-foreground-muted/80 leading-tight">
        <Info className="w-2.5 h-2.5 text-accent-cyan shrink-0 mt-0.5" />
        <span>
          Spatial proximity is contextual evidence only and does not constitute a definitive classification label on its own.
        </span>
      </div>
    </div>
  );
}
