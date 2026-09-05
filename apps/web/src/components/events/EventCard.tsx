"use client";

import React, { useMemo } from "react";
import {
  Flame,
  Trees,
  HelpCircle,
  AlertTriangle,
  Radio,
  MapPin,
  Clock,
  Zap,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { ThermalEvent } from "@/types/event";
import { calculateOperationalRisk, getRiskLevelStyles } from "@/lib/risk/scoring";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatHumanReadableLocation } from "@/lib/location/locationFilter";
import { formatFrp } from "@/lib/format/numbers";
import { formatRelativeSecondsAgo, formatUtcTime } from "@/lib/format/dates";
import { cn } from "@/lib/utils";

export interface EventCardProps {
  event: ThermalEvent;
  isSelected?: boolean;
  onSelect?: (event: ThermalEvent) => void;
  className?: string;
}

export function EventCard({
  event,
  isSelected = false,
  onSelect,
  className,
}: EventCardProps) {
  const isIndustrial = event.classification === "INDUSTRIAL";
  const isNonIndustrial = event.classification === "NON_INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";

  const risk = useMemo(() => calculateOperationalRisk(event), [event]);
  const riskStyles = useMemo(() => getRiskLevelStyles(risk.level), [risk.level]);

  const eventTimeMs = new Date(event.start_time).getTime();
  const elapsedSeconds = !isNaN(eventTimeMs)
    ? Math.max(0, Math.floor((Date.now() - eventTimeMs) / 1000))
    : 0;

  // Determine time label
  const timeDisplay = isNaN(eventTimeMs)
    ? "Recent"
    : `${formatUtcTime(event.start_time)} (${formatRelativeSecondsAgo(elapsedSeconds)})`;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect?.(event);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(event)}
      onKeyDown={handleKeyDown}
      className={cn(
        "group relative p-3 rounded-control border text-left transition-all duration-150 cursor-pointer select-none font-mono focus:outline-none focus:ring-1 focus:ring-accent",
        isSelected
          ? "bg-surface-raised border-accent shadow-panel ring-1 ring-accent/30"
          : "bg-surface/75 border-border/80 hover:bg-surface-raised/90 hover:border-border-strong",
        className
      )}
    >
      {/* 1. Header: Classification Badge, Operational Risk Tag & Time */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Classification Badge */}
          <Badge
            variant={
              isIndustrial
                ? "industrial"
                : isNonIndustrial
                ? "success"
                : "neutral"
            }
            size="sm"
            className="flex items-center gap-1 font-semibold"
          >
            {isIndustrial && <Flame className="w-2.5 h-2.5 text-accent animate-flame" />}
            {isNonIndustrial && <Trees className="w-2.5 h-2.5 text-state-success" />}
            {isUnknown && <HelpCircle className="w-2.5 h-2.5 text-accent-cyan" />}
            <span>{event.classification}</span>
          </Badge>

          {/* Derived Operational Risk Badge */}
          <span
            title={`Derived Operational Risk: ${risk.level} (${risk.score}/100)`}
            className={cn(
              "text-[9px] px-1.5 py-0.5 rounded border font-mono font-bold flex items-center gap-1",
              riskStyles.bg,
              riskStyles.text,
              riskStyles.border
            )}
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            <span>
              {risk.isIndeterminate ? "RISK: UNK" : `RISK: ${risk.level} ${risk.score}`}
            </span>
          </span>

          {isReviewRequired && (
            <Badge variant="warning" size="sm" className="flex items-center gap-1 text-[9px]">
              <AlertTriangle className="w-2.5 h-2.5 text-state-warning" />
              <span>REVIEW REQ</span>
            </Badge>
          )}

          {event.is_persistent && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-cyan/10 border border-accent-cyan/30 text-accent-cyan font-mono">
              PERSISTENT
            </span>
          )}
        </div>

        <div className="text-[10px] text-foreground-muted flex items-center gap-1 shrink-0">
          <Clock className="w-3 h-3 text-foreground-muted/70" />
          <span>{timeDisplay}</span>
        </div>
      </div>

      {/* 2. Spatial Context: Location & Coordinate Datum */}
      <div className="mb-2">
        <div className="text-xs font-semibold text-foreground group-hover:text-accent transition-colors truncate">
          {formatHumanReadableLocation(event)}
        </div>
        <div className="text-[11px] text-foreground-muted flex items-center gap-1 mt-0.5">
          <MapPin className="w-3 h-3 text-accent-cyan shrink-0" />
          <span>{formatCoordinate(event.latitude, event.longitude)}</span>
        </div>
      </div>

      {/* 3. Metric Strip: Model Confidence · Peak FRP · Detections */}
      <div className="grid grid-cols-3 gap-1.5 py-1.5 px-2 rounded bg-background/50 border border-border/40 text-[10px]">
        <div>
          <div className="text-foreground-muted text-[9px] uppercase">ML Conf.</div>
          <div className="font-semibold text-foreground">
            {(event.confidence * 100).toFixed(1)}%
          </div>
        </div>

        <div>
          <div className="text-foreground-muted text-[9px] uppercase">Peak FRP</div>
          <div className="font-semibold text-thermal-primary flex items-center gap-0.5">
            <Zap className="w-2.5 h-2.5" />
            {formatFrp(event.frp_mw)}
          </div>
        </div>

        <div>
          <div className="text-foreground-muted text-[9px] uppercase">Detections</div>
          <div className="font-semibold text-foreground-secondary flex items-center gap-1">
            <Radio className="w-2.5 h-2.5 text-accent" />
            {event.detection_count} obs
          </div>
        </div>
      </div>

      {/* 4. Sensor Instrument & Summary Footer */}
      {event.satellite_instrument && (
        <div className="mt-1.5 flex items-center justify-between text-[9px] text-foreground-muted">
          <span>Sensor: <strong className="text-foreground-secondary">{event.satellite_instrument}</strong></span>
          <span className="text-border-strong font-mono">{event.event_id}</span>
        </div>
      )}

      {/* Active Indicator Pillar */}
      {isSelected && (
        <div className="absolute top-0 left-0 bottom-0 w-1 bg-accent rounded-l-control shadow-[0_0_8px_rgba(255,106,0,0.8)]" />
      )}
    </div>
  );
}
