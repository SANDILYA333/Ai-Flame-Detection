"use client";

import React, { useState } from "react";
import type { AtmosphericDispersionResult } from "@/types/dispersion";
import { GripVertical, ChevronUp, ChevronDown, Layers } from "lucide-react";
import { useDraggable } from "@/hooks/useDraggable";
import { cn } from "@/lib/utils";

export interface FloatingWindLegendCardProps {
  dispersion: AtmosphericDispersionResult | null;
  className?: string;
}

export function FloatingWindLegendCard({
  dispersion,
  className,
}: FloatingWindLegendCardProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const { position, isDragging, cardRef, handlePointerDown } = useDraggable({
    storageKey: "pyrosat_floating_wind_legend_pos",
    defaultPosition: () => ({
      x: typeof window !== "undefined" ? Math.min(window.innerWidth - 240, 420) : 420,
      y: typeof window !== "undefined" ? Math.max(56, window.innerHeight - 220) : 580,
    }),
    boundsOffset: { top: 56, bottom: 64, left: 12, right: 12 },
  });

  if (!dispersion || !dispersion.dispersion) {
    return null;
  }

  const { dispersion: summary } = dispersion;

  return (
    <div
      ref={cardRef}
      style={{
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      className={cn(
        "z-35 w-[220px] pointer-events-auto select-none font-mono bg-surface-raised/95 backdrop-blur-md border border-border/90 rounded-panel shadow-panel flex flex-col transition-shadow duration-150 animate-in fade-in slide-in-from-bottom-2 duration-200",
        isDragging && "shadow-2xl ring-1 ring-accent-cyan/50",
        className
      )}
    >
      {/* Draggable Header */}
      <div
        onPointerDown={handlePointerDown}
        className={cn(
          "px-2.5 py-1.5 flex items-center justify-between border-border/60 transition-colors select-none",
          isCollapsed ? "border-b-0" : "border-b pb-1.5",
          isDragging ? "cursor-grabbing bg-surface-hover/60" : "cursor-grab hover:bg-surface-hover/30"
        )}
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <GripVertical className="w-3 h-3 text-foreground-muted shrink-0" />
          <span className="text-[9px] font-bold text-foreground uppercase tracking-wider truncate">
            WIND &amp; PLUME LEGEND
          </span>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[8.5px] px-1 py-0.2 rounded border bg-accent-cyan/15 border-accent-cyan/30 text-accent-cyan font-bold">
            CLASS {summary.stability_class}
          </span>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsCollapsed(!isCollapsed);
            }}
            title={isCollapsed ? "Expand legend" : "Collapse legend"}
            aria-label={isCollapsed ? "Expand legend" : "Collapse legend"}
            className="p-0.5 rounded text-foreground-muted hover:text-foreground hover:bg-surface-hover active:scale-95 transition-all"
          >
            {isCollapsed ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronUp className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded Legend Content */}
      {!isCollapsed && (
        <div className="p-2.5 space-y-1.5 text-foreground-secondary text-[9px] animate-in fade-in duration-150">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-state-error border border-white shrink-0" />
            <span className="truncate">Thermal Incident Origin</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full border border-state-error/80 bg-state-error/20 shrink-0" />
            <span className="truncate">200m Modeled Isolation</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 border border-state-warning border-dashed bg-state-warning/15 shrink-0 rounded-xs" />
            <span className="truncate">Evacuation Corridor</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 border border-accent-cyan bg-accent-cyan/20 shrink-0 rounded-xs" />
            <span className="truncate">Gaussian Hazard Plume</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-state-error shrink-0" />
            <span className="truncate">Downwind Trajectory</span>
          </div>
        </div>
      )}
    </div>
  );
}
