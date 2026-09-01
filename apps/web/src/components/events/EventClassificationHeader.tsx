"use client";

import React from "react";
import { ThermalEvent } from "@/types/event";
import { Badge } from "@/components/ui/Badge";
import {
  Flame,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  Radio,
  Zap,
} from "lucide-react";
import { formatPercent } from "@/lib/format/numbers";
import { cn } from "@/lib/utils";

export interface EventClassificationHeaderProps {
  event: ThermalEvent;
  operatingMode?: string;
  className?: string;
}

export function EventClassificationHeader({
  event,
  operatingMode = "HIGH_PRECISION",
  className,
}: EventClassificationHeaderProps) {
  const isIndustrial = event.classification === "INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";
  const isAbstained = isUnknown || isReviewRequired || event.confidence < 0.70;

  const modeTooltip =
    operatingMode === "HIGH_PRECISION"
      ? "Prioritizes highly reliable positive industrial classifications."
      : operatingMode === "HIGH_RECALL"
      ? "Prioritizes detecting all potential industrial thermal events."
      : "Presents classifications only when confidence satisfies the operational threshold.";

  return (
    <div className={cn("space-y-2 font-mono", className)}>
      {/* 1. Classification & Operating Mode Strip */}
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge
            variant={
              isIndustrial
                ? "industrial"
                : isUnknown
                ? "neutral"
                : "warning"
            }
            className="font-bold tracking-wide text-xs px-2.5 py-0.5"
          >
            {event.classification}
          </Badge>

          <Badge variant="thermal" className="text-[10px]">
            {event.phenomenon}
          </Badge>

          {isReviewRequired ? (
            <Badge variant="warning" className="animate-pulse-subtle text-[10px]">
              <AlertTriangle className="w-2.5 h-2.5 mr-1 text-state-warning" />
              REVIEW REQUIRED
            </Badge>
          ) : (
            <Badge variant="success" className="text-[10px]">
              <ShieldCheck className="w-2.5 h-2.5 mr-1 text-accent" />
              CONFIDENT
            </Badge>
          )}
        </div>

        {/* Active Operating Mode Pill */}
        <div
          title={modeTooltip}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface border border-border/80 text-[9px] text-foreground-muted cursor-help"
        >
          <Zap className="w-2.5 h-2.5 text-accent-cyan" />
          <span>{operatingMode}</span>
        </div>
      </div>

      {/* 2. Confidence Indicator Bar */}
      <div className="p-2 rounded-control bg-surface/70 border border-border/70 text-[11px] space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Radio className="w-3 h-3 text-accent" />
            Decision Confidence
          </span>
          <span className="font-bold text-foreground">
            {formatPercent(event.confidence, 1)}
          </span>
        </div>

        <div className="w-full h-1.5 bg-background rounded-full overflow-hidden border border-border/40">
          <div
            className={cn(
              "h-full transition-all duration-300",
              isIndustrial
                ? "bg-accent"
                : isUnknown
                ? "bg-accent-cyan"
                : "bg-state-warning"
            )}
            style={{ width: `${Math.min(100, Math.max(0, event.confidence * 100))}%` }}
          />
        </div>
      </div>

      {/* 3. Dedicated UNKNOWN / Abstention Explanation Banner */}
      {isUnknown && (
        <div className="flex items-start gap-2 p-2 bg-accent-cyan/10 border border-accent-cyan/30 rounded-control text-[11px] text-accent-cyan leading-tight">
          <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">UNRESOLVED ORTHOGONAL CLASSIFICATION</div>
            <div className="text-[10px] text-foreground-muted mt-0.5">
              Model confidence is below the operational acceptance threshold (0.70). This event represents true uncertainty and requires multi-source human review.
            </div>
          </div>
        </div>
      )}

      {isReviewRequired && !isUnknown && (
        <div className="flex items-start gap-2 p-2 bg-state-warning/10 border border-state-warning/30 rounded-control text-[11px] text-state-warning leading-tight">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">INTERMITTENT TEMPORAL PROFILE</div>
            <div className="text-[10px] text-foreground-muted mt-0.5">
              Insufficient longitudinal observation history to confirm persistent stationary facility attribution.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
