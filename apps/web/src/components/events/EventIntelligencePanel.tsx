"use client";

import React, { useMemo } from "react";
import { ThermalEvent } from "@/types/event";
import { useEventDetail } from "@/hooks/useEventDetail";
import { Badge } from "@/components/ui/Badge";
import { ExplainableAiSection } from "./ExplainableAiSection";
import { IndustrialAssetSection } from "./IndustrialAssetSection";
import { calculateOperationalRisk, getRiskLevelStyles } from "@/lib/risk/scoring";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatFrp, formatPercent } from "@/lib/format/numbers";
import { formatUtcDateTime } from "@/lib/format/dates";
import { APP_CONFIG } from "@/config/ui";
import {
  Flame,
  Activity,
  Radio,
  MapPin,
  Clock,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  X,
  Layers,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  Cpu,
  Satellite,
  Building2,
  CheckCircle2,
  ShieldAlert,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface EventIntelligencePanelProps {
  event: ThermalEvent | null;
  currentIndex?: number;
  totalEvents?: number;
  onPrevEvent?: () => void;
  onNextEvent?: () => void;
  onCenterMap?: () => void;
  onClose: () => void;
  className?: string;
}

export function EventIntelligencePanel({
  event,
  currentIndex = 0,
  totalEvents = 0,
  onPrevEvent,
  onNextEvent,
  onCenterMap,
  onClose,
  className,
}: EventIntelligencePanelProps) {
  const { detail, timeline, evidence, intelligence, isLoading } = useEventDetail(
    event?.event_id
  );

  // Compute operational risk assessment
  const risk = useMemo(() => {
    if (!event) return null;
    return calculateOperationalRisk(event);
  }, [event]);

  const riskStyles = useMemo(() => {
    if (!risk) return null;
    return getRiskLevelStyles(risk.level);
  }, [risk]);

  if (!event || !risk || !riskStyles) {
    return (
      <div
        className={cn(
          "w-full sm:w-88 bg-surface-raised/95 backdrop-blur-md border border-border rounded-panel p-4 shadow-panel pointer-events-auto text-foreground-muted font-mono text-xs text-center",
          className
        )}
      >
        <div className="w-8 h-8 rounded-full bg-surface-hover mx-auto flex items-center justify-center mb-2">
          <Flame className="w-4 h-4 text-foreground-muted" />
        </div>
        <div className="font-semibold text-foreground">NO EVENT SELECTED</div>
        <p className="text-[11px] text-foreground-muted mt-1">
          Select a thermal anomaly on the map to inspect its real-time intelligence.
        </p>
      </div>
    );
  }

  const isIndustrial = event.classification === "INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";

  return (
    <div
      className={cn(
        "w-full sm:w-96 max-h-[58vh] sm:max-h-[85vh] overflow-y-auto bg-surface-raised/95 backdrop-blur-md border border-border rounded-t-panel sm:rounded-panel p-3.5 sm:p-4 shadow-panel pointer-events-auto flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-3 duration-200 select-none scrollbar-thin",
        className
      )}
    >
      {/* 1. Header with Event ID, Navigation & Controls */}
      <div className="flex items-start justify-between gap-2 border-b border-border pb-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              "w-7 h-7 sm:w-8 sm:h-8 rounded-control flex items-center justify-center shrink-0 border",
              isIndustrial
                ? "bg-accent/15 border-accent/30 text-accent"
                : isUnknown
                ? "bg-accent-cyan/15 border-accent-cyan/30 text-accent-cyan"
                : "bg-state-warning/15 border-state-warning/30 text-state-warning"
            )}
          >
            <Flame className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-flame" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 font-mono">
              <span className="text-xs font-bold text-foreground tracking-wider truncate">
                {event.event_id}
              </span>
              {totalEvents > 1 && (
                <span className="text-[10px] text-foreground-muted px-1.5 py-0.5 rounded bg-surface border border-border/60 shrink-0">
                  {String(currentIndex + 1).padStart(2, "0")}/{String(totalEvents).padStart(2, "0")}
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono text-foreground-muted truncate max-w-[170px]">
              {event.location_name || "Spatial Anomaly Cluster"}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {onPrevEvent && (
            <button
              onClick={onPrevEvent}
              title="Previous Event (←)"
              aria-label="Previous Event"
              className="p-1 text-foreground-muted hover:text-foreground rounded-control hover:bg-surface-hover active:scale-95 transition-all"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          )}
          {onNextEvent && (
            <button
              onClick={onNextEvent}
              title="Next Event (→)"
              aria-label="Next Event"
              className="p-1 text-foreground-muted hover:text-foreground rounded-control hover:bg-surface-hover active:scale-95 transition-all"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
          {onCenterMap && (
            <button
              onClick={onCenterMap}
              title="Center Map on Target"
              aria-label="Center Map"
              className="p-1 text-foreground-muted hover:text-accent rounded-control hover:bg-surface-hover active:scale-95 transition-all"
            >
              <Crosshair className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            title="Close Panel (Esc)"
            aria-label="Close Panel"
            className="p-1 text-foreground-muted hover:text-state-error rounded-control hover:bg-surface-hover active:scale-95 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. Scientific Classification & Uncertainty Taxonomy */}
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge
            variant={
              isIndustrial
                ? "industrial"
                : isUnknown
                ? "neutral"
                : "warning"
            }
            className="font-bold tracking-wide"
          >
            {event.classification}
          </Badge>

          <Badge variant="thermal" className="font-mono">
            {event.phenomenon}
          </Badge>

          {isReviewRequired ? (
            <Badge variant="warning" className="animate-pulse-subtle font-mono">
              <AlertTriangle className="w-2.5 h-2.5 mr-1 text-state-warning" />
              REVIEW REQUIRED
            </Badge>
          ) : (
            <Badge variant="success" className="font-mono">
              <ShieldCheck className="w-2.5 h-2.5 mr-1 text-accent" />
              CONFIDENT
            </Badge>
          )}
        </div>

        {/* Dedicated Abstention / Uncertainty Banner */}
        {isUnknown && (
          <div className="flex items-start gap-2 p-2 bg-accent-cyan/10 border border-accent-cyan/30 rounded-control text-[11px] font-mono text-accent-cyan leading-tight">
            <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold">UNRESOLVED ORTHOGONAL CLASSIFICATION</div>
              <div className="text-[10px] text-foreground-muted mt-0.5">
                Model confidence is below operational threshold (0.70). Multi-source evidence review recommended.
              </div>
            </div>
          </div>
        )}

        {isReviewRequired && !isUnknown && (
          <div className="flex items-start gap-2 p-2 bg-state-warning/10 border border-state-warning/30 rounded-control text-[11px] font-mono text-state-warning leading-tight">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold">INTERMITTENT TEMPORAL PROFILE</div>
              <div className="text-[10px] text-foreground-muted mt-0.5">
                Insufficient longitudinal observation history to confirm persistent facility attribution.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Industrial Infrastructure & Nearby Asset Intelligence */}
      <IndustrialAssetSection event={event} evidence={evidence} />

      {/* 4. Explainable AI (XAI) Grounded Reasoning Section */}
      <ExplainableAiSection
        event={event}
        evidence={evidence}
        intelligence={intelligence}
      />

      {/* 5. Operational Risk & Severity Assessment Card */}
      <div className="p-2.5 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-accent" />
            Operational Risk Assessment
          </span>
          <span
            className={cn(
              "text-[10px] px-2 py-0.5 rounded border font-bold",
              riskStyles.bg,
              riskStyles.text,
              riskStyles.border
            )}
          >
            {risk.level} {risk.isIndeterminate ? "" : `(${risk.score}/100)`}
          </span>
        </div>

        {/* Score Progress Bar */}
        {!risk.isIndeterminate && (
          <div className="w-full h-1.5 bg-background rounded-full overflow-hidden border border-border/40">
            <div
              className={cn(
                "h-full transition-all duration-300",
                risk.level === "CRITICAL"
                  ? "bg-state-error"
                  : risk.level === "HIGH"
                  ? "bg-accent"
                  : risk.level === "MEDIUM"
                  ? "bg-state-warning"
                  : "bg-state-success"
              )}
              style={{ width: `${risk.score}%` }}
            />
          </div>
        )}

        {/* Risk Drivers Breakdown (WHY?) */}
        <div className="space-y-1 pt-1 border-t border-border/40 text-[10px]">
          <div className="text-[9px] uppercase tracking-wider text-foreground-muted font-semibold">
            Contributing Drivers (Why?)
          </div>
          {risk.factors.map((f, i) => (
            <div key={i} className="flex items-center justify-between text-foreground-secondary">
              <span className="truncate max-w-[200px]">{f.description}</span>
              <span className="font-semibold text-foreground shrink-0 ml-1">
                +{f.points} pts
              </span>
            </div>
          ))}
        </div>

        {/* Derived Heuristic Disclaimer */}
        <div className="flex items-start gap-1 text-[8.5px] text-foreground-muted/80 leading-tight pt-1">
          <Info className="w-2.5 h-2.5 text-accent-cyan shrink-0 mt-0.5" />
          <span>{risk.disclaimer}</span>
        </div>
      </div>

      {/* 6. Primary Key Metrics Grid (FRP, ML Conf, Detections) */}
      <div className="grid grid-cols-3 gap-2 bg-surface/70 rounded-control p-2.5 border border-border/70 text-xs font-mono">
        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3 h-3 text-thermal-primary" />
            FRP Peak
          </div>
          <div className="text-sm font-bold text-thermal-primary mt-0.5">
            {formatFrp(event.frp_mw)}
          </div>
        </div>

        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Radio className="w-3 h-3 text-accent" />
            ML Conf.
          </div>
          <div className="text-sm font-bold text-foreground mt-0.5">
            {formatPercent(event.confidence, 1)}
          </div>
        </div>

        <div>
          <div className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
            <Layers className="w-3 h-3 text-accent-cyan" />
            Detections
          </div>
          <div className="text-sm font-bold text-accent-cyan mt-0.5">
            {event.detection_count} pts
          </div>
        </div>
      </div>

      {/* 7. Geographic & Contextual Infrastructure Evidence */}
      <div className="space-y-2 text-[11px] font-mono border-t border-border/70 pt-2">
        <div className="flex items-start gap-2 text-foreground-secondary">
          <MapPin className="w-3.5 h-3.5 text-accent-cyan shrink-0 mt-0.5" />
          <div className="leading-tight">
            <div className="font-semibold text-foreground">
              {formatCoordinate(event.latitude, event.longitude)}
            </div>
            <div className="text-[10px] text-foreground-muted">
              Centroid: WGS-84 Datum (EPSG:4326)
            </div>
          </div>
        </div>

        {event.context_summary && (
          <div className="flex items-start gap-2 text-foreground-muted text-[10px] bg-surface/50 p-2 rounded-control border border-border/50 leading-relaxed">
            <Building2 className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
            <div>
              <span className="text-foreground-secondary font-semibold">Evidence: </span>
              <span>{event.context_summary}</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-[10px] text-foreground-muted">
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

      {/* 8. Provenance & Scientific Lineage Footer */}
      <div className="mt-auto pt-2 border-t border-border/50 flex items-center justify-between text-[10px] font-mono text-foreground-muted">
        <div className="flex items-center gap-1">
          <Cpu className="w-3 h-3 text-accent" />
          <span>Lineage: {APP_CONFIG.featureSchema}</span>
        </div>
        <div className="flex items-center gap-1 text-accent">
          <CheckCircle2 className="w-3 h-3" />
          <span>NASA FIRMS Calibrated</span>
        </div>
      </div>
    </div>
  );
}
