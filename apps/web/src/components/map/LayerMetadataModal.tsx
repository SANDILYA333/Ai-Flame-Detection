"use client";

import React from "react";
import { GisLayerItem } from "@/types/layer";
import { Info, X, Database, Eye, AlertCircle, RefreshCw } from "lucide-react";

export interface LayerMetadataModalProps {
  layer: GisLayerItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export function LayerMetadataModal({
  layer,
  isOpen,
  onClose,
}: LayerMetadataModalProps) {
  if (!isOpen || !layer) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-surface-raised border border-border rounded-modal shadow-modal flex flex-col font-mono overflow-hidden text-foreground">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-accent/15 border border-accent/30 text-accent">
              <Info className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-foreground">
                {layer.label}
              </div>
              <div className="text-[9px] text-foreground-muted">
                GIS Layer Provenance & Interpretation Specification
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3 text-[11px]">
          <div className="p-2.5 rounded bg-surface border border-border/80 text-[10px] space-y-1">
            <div className="text-foreground-muted uppercase text-[8.5px] flex items-center gap-1">
              <Database className="w-3 h-3 text-accent" />
              <span>Layer Description</span>
            </div>
            <div className="text-foreground-secondary leading-relaxed">
              {layer.description}
            </div>
          </div>

          <div className="p-2.5 rounded bg-surface border border-border/80 text-[10px] space-y-1">
            <div className="text-foreground-muted uppercase text-[8.5px] flex items-center gap-1">
              <Eye className="w-3 h-3 text-accent-cyan" />
              <span>Operational Interpretation</span>
            </div>
            <div className="text-foreground-secondary leading-relaxed">
              Subpixel thermal radiative excess or spatial infrastructure perimeters used as context signals for multi-modal classification and hazard isolation.
            </div>
          </div>

          <div className="p-2.5 rounded bg-state-warning/10 border border-state-warning/30 text-[10px] space-y-1">
            <div className="text-state-warning uppercase text-[8.5px] font-bold flex items-center gap-1">
              <AlertCircle className="w-3 h-3 text-state-warning" />
              <span>Scientific Limitations & Invariants</span>
            </div>
            <div className="text-foreground-secondary leading-relaxed">
              Infrastructure proximity indicates spatial context, NOT autonomous incident attribution. Ground observations require analyst confirmation.
            </div>
          </div>

          <div className="flex items-center justify-between text-[9px] text-foreground-muted pt-1">
            <span className="flex items-center gap-1">
              <RefreshCw className="w-2.5 h-2.5" />
              <span>Update Frequency: Every 3 Hours / Orbit Pass</span>
            </span>
            <span>Category: {layer.category.toUpperCase()}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-border bg-surface flex justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-surface-hover hover:bg-surface border border-border text-[10px] text-foreground font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
