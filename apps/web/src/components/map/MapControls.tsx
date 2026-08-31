"use client";

import React from "react";
import { Plus, Minus, Home, Layers, Maximize2 } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

export interface MapControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetHome?: () => void;
  onToggleLayers?: () => void;
  layersActive?: boolean;
  className?: string;
}

export function MapControls({
  onZoomIn,
  onZoomOut,
  onResetHome,
  onToggleLayers,
  layersActive = false,
  className,
}: MapControlsProps) {
  return (
    <div className={cn("flex flex-col gap-1.5 bg-surface/85 backdrop-blur-md p-1 rounded-panel border border-border shadow-panel", className)}>
      <Tooltip content="Zoom In (+)" position="left">
        <IconButton ariaLabel="Zoom In" size="sm" onClick={onZoomIn}>
          <Plus className="w-3.5 h-3.5" />
        </IconButton>
      </Tooltip>

      <Tooltip content="Zoom Out (-)" position="left">
        <IconButton ariaLabel="Zoom Out" size="sm" onClick={onZoomOut}>
          <Minus className="w-3.5 h-3.5" />
        </IconButton>
      </Tooltip>

      <Tooltip content="Reset View (⌂)" position="left">
        <IconButton ariaLabel="Reset View" size="sm" onClick={onResetHome}>
          <Home className="w-3.5 h-3.5" />
        </IconButton>
      </Tooltip>

      <div className="h-[1px] bg-border my-0.5" />

      <Tooltip content="Toggle GIS Layers" position="left">
        <IconButton
          ariaLabel="Toggle GIS Layers"
          size="sm"
          variant={layersActive ? "active" : "default"}
          onClick={onToggleLayers}
        >
          <Layers className="w-3.5 h-3.5" />
        </IconButton>
      </Tooltip>

      <Tooltip content="Fullscreen Mode" position="left">
        <IconButton
          ariaLabel="Fullscreen"
          size="sm"
          onClick={() => {
            if (!document.fullscreenElement) {
              document.documentElement.requestFullscreen().catch(() => {});
            } else {
              document.exitFullscreen().catch(() => {});
            }
          }}
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </IconButton>
      </Tooltip>
    </div>
  );
}
