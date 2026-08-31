"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface MapOverlayContainerProps {
  children?: React.ReactNode;
  controls?: React.ReactNode;
  hud?: React.ReactNode;
  leftPanel?: React.ReactNode;
  rightPanel?: React.ReactNode;
  selectedEventCard?: React.ReactNode;
  className?: string;
}

export function MapOverlayContainer({
  children,
  controls,
  hud,
  leftPanel,
  rightPanel,
  selectedEventCard,
  className,
}: MapOverlayContainerProps) {
  return (
    <div className={cn("absolute inset-0 pointer-events-none overflow-hidden z-20", className)}>
      {/* 1. Top HUD Area (Coordinates, Mode Switcher, Quick Actions) */}
      {hud && <div className="absolute top-3 left-3 right-3 z-20 pointer-events-none">{hud}</div>}

      {/* 2. Left Floating Panel Region (GIS Layers) */}
      {leftPanel && (
        <div className="absolute top-16 left-3 z-30 pointer-events-auto animate-in fade-in slide-in-from-left-4 duration-200">
          {leftPanel}
        </div>
      )}

      {/* 3. Right Floating Panel Region (Thermal Intelligence) */}
      {rightPanel && (
        <div className="absolute top-16 right-3 z-30 pointer-events-auto animate-in fade-in slide-in-from-right-4 duration-200">
          {rightPanel}
        </div>
      )}

      {/* 4. Bottom-Left / Responsive Bottom Sheet Selected Event Snapshot Card */}
      {selectedEventCard && (
        <div className="absolute bottom-0 sm:bottom-6 inset-x-0 sm:inset-x-auto sm:left-3 z-40 pointer-events-auto">
          {selectedEventCard}
        </div>
      )}

      {/* 5. Bottom Right Navigation Controls */}
      {controls && (
        <div className="absolute bottom-6 right-3 z-20 pointer-events-auto">
          {controls}
        </div>
      )}

      {/* 6. Direct Child Overlays */}
      {children}
    </div>
  );
}
