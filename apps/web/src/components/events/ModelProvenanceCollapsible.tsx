"use client";

import React, { useState } from "react";
import type { ModelProvenance } from "@/types/xai";
import { APP_CONFIG } from "@/config/ui";
import {
  Cpu,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  CheckCircle2,
  FileCode2,
  Database,
  Sliders,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ModelProvenanceCollapsibleProps {
  provenance: ModelProvenance;
  className?: string;
}

export function ModelProvenanceCollapsible({
  provenance,
  className,
}: ModelProvenanceCollapsibleProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      className={cn(
        "rounded-control bg-surface/60 border border-border/70 font-mono text-[11px] overflow-hidden transition-all",
        className
      )}
    >
      {/* Collapsible Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-2 flex items-center justify-between text-foreground-secondary hover:text-foreground hover:bg-surface-hover/50 transition-colors text-left"
      >
        <div className="flex items-center gap-1.5 font-bold text-[10px] uppercase tracking-wider text-foreground">
          <Cpu className="w-3.5 h-3.5 text-accent" />
          <span>Model Provenance & Lineage</span>
        </div>

        <div className="flex items-center gap-1.5 text-foreground-muted text-[10px]">
          <span>{provenance.modelVersion}</span>
          {isOpen ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </div>
      </button>

      {/* Expanded Provenance Content */}
      {isOpen && (
        <div className="p-2.5 pt-1 space-y-2 border-t border-border/50 text-[10px] bg-background/30 animate-in fade-in duration-150">
          <div className="grid grid-cols-2 gap-2">
            <div className="p-1.5 rounded bg-surface/50 border border-border/40">
              <div className="text-[9px] text-foreground-muted uppercase">Architecture</div>
              <div className="font-semibold text-foreground truncate mt-0.5">
                {provenance.modelName}
              </div>
            </div>

            <div className="p-1.5 rounded bg-surface/50 border border-border/40">
              <div className="text-[9px] text-foreground-muted uppercase">Feature Schema</div>
              <div className="font-semibold text-accent-cyan truncate mt-0.5">
                {provenance.featureSchema} (30 dims)
              </div>
            </div>

            <div className="p-1.5 rounded bg-surface/50 border border-border/40">
              <div className="text-[9px] text-foreground-muted uppercase">Operating Policy</div>
              <div className="font-semibold text-accent truncate mt-0.5">
                {provenance.operatingMode}
              </div>
            </div>

            <div className="p-1.5 rounded bg-surface/50 border border-border/40">
              <div className="text-[9px] text-foreground-muted uppercase">Acceptance Gate</div>
              <div className="font-semibold text-foreground truncate mt-0.5">
                {(provenance.decisionThreshold * 100).toFixed(0)}% Threshold
              </div>
            </div>
          </div>

          <div className="p-1.5 rounded bg-surface/30 border border-border/30 text-[9px] text-foreground-muted space-y-1">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Database className="w-3 h-3 text-accent-cyan" /> Data Source:
              </span>
              <span className="font-semibold text-foreground">NASA FIRMS (VIIRS/MODIS)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Sliders className="w-3 h-3 text-accent" /> Ingestion Pipeline:
              </span>
              <span className="font-semibold text-foreground">Spatial-Temporal Aggregator</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-state-success" /> Verification:
              </span>
              <span className="font-semibold text-state-success">NASA Calibrated Baseline</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
