"use client";

import React from "react";
import { ThermalEvent } from "@/types/event";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatHumanReadableLocation } from "@/lib/location/locationFilter";
import { formatFrp } from "@/lib/format/numbers";
import { formatUtcDateTime } from "@/lib/format/dates";
import {
  Activity,
  Layers,
  MapPin,
  Clock,
  Satellite,
  Building2,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface EventOverviewGridProps {
  event: ThermalEvent;
  className?: string;
}

export function EventOverviewGrid({ event, className }: EventOverviewGridProps) {
  return (
    <div className={cn("space-y-2 font-mono text-xs", className)}>
      {/* 1. FRP Peak, Detections, and Observation Count */}
      <div className="grid grid-cols-2 gap-2 bg-surface/70 rounded-control p-2.5 border border-border/70">
        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3 h-3 text-thermal-primary" />
            Peak Radiative Power
          </div>
          <div className="text-sm font-bold text-thermal-primary mt-0.5">
            {formatFrp(event.frp_mw)}
          </div>
        </div>

        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Layers className="w-3 h-3 text-accent-cyan" />
            Cluster Detections
          </div>
          <div className="text-sm font-bold text-accent-cyan mt-0.5">
            {event.detection_count} observations
          </div>
        </div>
      </div>

      {/* 2. Geographic Centroid & Spatial Provenance */}
      <div className="p-2.5 rounded-control bg-surface/50 border border-border/60 space-y-1.5 text-[11px]">
        <div className="flex items-start gap-2 text-foreground-secondary">
          <MapPin className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
          <div className="leading-tight">
            <div className="font-semibold text-foreground">
              {formatHumanReadableLocation(event)}
            </div>
            <div className="text-[10px] text-accent font-semibold mt-0.5">
              Coordinates: {formatCoordinate(event.latitude, event.longitude)}
            </div>
            <div className="text-[9.5px] text-foreground-muted mt-0.5">
              Centroid: WGS-84 Datum (EPSG:4326) · High Precision Spatial Fix
            </div>
          </div>
        </div>

        {event.context_summary && (
          <div className="flex items-start gap-2 text-foreground-muted text-[10px] bg-background/40 p-1.5 rounded border border-border/40 leading-relaxed">
            <Building2 className="w-3 h-3 text-accent shrink-0 mt-0.5" />
            <div>
              <span className="text-foreground-secondary font-semibold">Context: </span>
              <span>{event.context_summary}</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-[10px] text-foreground-muted border-t border-border/40 pt-1">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatUtcDateTime(event.start_time)}
          </span>
          <span className="flex items-center gap-1 text-accent-cyan">
            <Satellite className="w-3 h-3" />
            {event.satellite_instrument || "VIIRS NOAA-20/21"}
          </span>
        </div>
      </div>
    </div>
  );
}
