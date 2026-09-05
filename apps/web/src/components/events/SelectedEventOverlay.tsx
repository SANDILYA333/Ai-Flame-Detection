"use client";

import React from "react";
import { ThermalEvent } from "@/types/event";
import { Badge } from "@/components/ui/Badge";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatHumanReadableLocation } from "@/lib/location/locationFilter";
import { formatFrp, formatPercent } from "@/lib/format/numbers";
import { formatUtcDateTime } from "@/lib/format/dates";
import {
  Flame,
  Activity,
  Radio,
  MapPin,
  Clock,
  ShieldCheck,
  AlertTriangle,
  X,
  Layers,
} from "lucide-react";

export interface SelectedEventOverlayProps {
  event: ThermalEvent | null;
  onClose: () => void;
  className?: string;
}

export function SelectedEventOverlay({
  event,
  onClose,
  className,
}: SelectedEventOverlayProps) {
  if (!event) return null;

  const isIndustrial = event.classification === "INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";

  return (
    <div
      className="w-80 bg-surface-raised/95 backdrop-blur-md border border-border rounded-panel p-4 shadow-panel pointer-events-auto animate-in fade-in slide-in-from-bottom-4 duration-200"
    >
      {/* Header with Event ID and Close Button */}
      <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-control bg-thermal-primary/15 border border-thermal-primary/30 flex items-center justify-center text-thermal-primary">
            <Flame className="w-4 h-4 animate-flame" />
          </div>
          <div>
            <div className="text-xs font-mono font-bold text-foreground tracking-wider">
              {event.event_id}
            </div>
            <div className="text-[10px] font-mono text-foreground-muted">
              {event.source_id || "DYNAMIC CLUSTER"}
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          aria-label="Close event details"
          className="p-1 text-foreground-muted hover:text-foreground rounded-control hover:bg-surface-hover transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 my-3">
        <Badge
          variant={
            isIndustrial
              ? "industrial"
              : isUnknown
              ? "neutral"
              : "warning"
          }
        >
          {event.classification}
        </Badge>

        <Badge variant="thermal">{event.phenomenon}</Badge>

        {isReviewRequired ? (
          <Badge variant="warning">
            <AlertTriangle className="w-2.5 h-2.5 mr-1" />
            REVIEW REQUIRED
          </Badge>
        ) : (
          <Badge variant="success">
            <ShieldCheck className="w-2.5 h-2.5 mr-1" />
            CONFIDENT
          </Badge>
        )}
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 bg-surface/60 rounded-control p-2.5 border border-border/60 text-xs font-mono mb-3">
        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3 h-3 text-thermal-primary" />
            Thermal FRP
          </div>
          <div className="text-sm font-bold text-thermal-primary mt-0.5">
            {formatFrp(event.frp_mw)}
          </div>
        </div>

        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Radio className="w-3 h-3 text-accent-cyan" />
            Confidence
          </div>
          <div className="text-sm font-bold text-foreground mt-0.5">
            {formatPercent(event.confidence, 1)}
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="space-y-1 mb-3">
        <div className="flex justify-between text-[10px] font-mono text-foreground-muted">
          <span>AI MODEL PROBABILITY</span>
          <span>{(event.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, Math.max(0, event.confidence * 100))}%` }}
          />
        </div>
      </div>

      {/* Geographic & Contextual Metadata */}
      <div className="space-y-2 text-[11px] font-mono border-t border-border pt-2.5">
        <div className="flex items-start gap-1.5 text-foreground-secondary">
          <MapPin className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-foreground">
              {formatHumanReadableLocation(event)}
            </div>
            <div className="text-[10px] text-foreground-muted">
              Coordinates: {formatCoordinate(event.latitude, event.longitude)}
            </div>
          </div>
        </div>

        {event.context_summary && (
          <div className="flex items-start gap-1.5 text-foreground-muted text-[10px] bg-surface/40 p-2 rounded border border-border/40 leading-relaxed">
            <Layers className="w-3 h-3 text-accent-cyan shrink-0 mt-0.5" />
            <span>{event.context_summary}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-[10px] text-foreground-muted pt-1">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatUtcDateTime(event.start_time)}
          </span>
          <span>{event.detection_count} Detections</span>
        </div>
      </div>
    </div>
  );
}
