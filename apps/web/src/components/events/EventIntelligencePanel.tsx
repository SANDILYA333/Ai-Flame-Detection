"use client";

import React, { useState, useMemo } from "react";
import { ThermalEvent } from "@/types/event";
import { useEventDetail } from "@/hooks/useEventDetail";
import { EventClassificationHeader } from "./EventClassificationHeader";
import { ClassProbabilityBreakdown } from "./ClassProbabilityBreakdown";
import { EventOverviewGrid } from "./EventOverviewGrid";
import { IndustrialAssetSection } from "./IndustrialAssetSection";
import { ExplainableAiSection } from "./ExplainableAiSection";
import { PlanckPyrometrySection } from "./PlanckPyrometrySection";
import { HistoricalCurveSection } from "./HistoricalCurveSection";
import { HazmatRiskCard } from "./HazmatRiskCard";
import { ModelProvenanceCollapsible } from "./ModelProvenanceCollapsible";
import { EventDetailSkeleton } from "./EventDetailSkeleton";
import { EventDetailError } from "./EventDetailError";
import { generateXaiExplanation } from "@/lib/xai/explainer";
import { calculateOperationalRisk, getRiskLevelStyles } from "@/lib/risk/scoring";
import { EmergencyResponseSection } from "./EmergencyResponse/EmergencyResponseSection";
import { TacticalDossierModal } from "@/components/dossier/TacticalDossierModal";
import { APP_CONFIG } from "@/config/ui";
import {
  Flame,
  X,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  ShieldAlert,
  Info,
  CheckCircle2,
  Cpu,
  FileText,
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
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);

  const {
    evidence,
    intelligence,
    isLoading,
    isError,
    error,
    refetch,
  } = useEventDetail(event?.event_id);

  // Compute operational risk assessment
  const risk = useMemo(() => {
    if (!event) return null;
    return calculateOperationalRisk(event);
  }, [event]);

  const riskStyles = useMemo(() => {
    if (!risk) return null;
    return getRiskLevelStyles(risk.level);
  }, [risk]);

  // Compute grounded XAI explanation
  const xai = useMemo(() => {
    if (!event) return null;
    return generateXaiExplanation(event, evidence, intelligence);
  }, [event, evidence, intelligence]);

  if (!event || !risk || !riskStyles || !xai) {
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

  if (isError && !evidence) {
    return (
      <EventDetailError
        message={error?.message || "Failed to load event intelligence"}
        onRetry={refetch}
        onClose={onClose}
        className={className}
      />
    );
  }

  const isIndustrial = event.classification === "INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";

  return (
    <>
      <div
        className={cn(
          "w-full sm:w-96 max-h-[60vh] sm:max-h-[86vh] overflow-y-auto bg-surface-raised/95 backdrop-blur-md border border-border rounded-t-panel sm:rounded-panel p-3.5 sm:p-4 shadow-panel pointer-events-auto flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-3 duration-200 select-none scrollbar-thin",
          className
        )}
      >
        {/* 1. Header with Event ID, Pagination Navigation & Controls */}
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

          {/* Action Controls */}
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
              type="button"
              onClick={onClose}
              title="Minimize / Close Panel (Esc)"
              aria-label="Close event intelligence panel"
              className="p-1 text-foreground-muted hover:text-state-error rounded-control hover:bg-surface-hover active:scale-95 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tactical Dossier Trigger Button */}
        <button
          onClick={() => setIsDossierModalOpen(true)}
          className="w-full py-1.5 px-3 rounded-control bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent text-[10px] font-mono font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>OPEN TACTICAL INCIDENT BRIEFING (DOSSIER)</span>
        </button>

        {isLoading && !evidence ? (
          <EventDetailSkeleton />
        ) : (
          <>
            {/* Level 1 & 2: Classification, Confidence & Operating Policy */}
            <EventClassificationHeader
              event={event}
              operatingMode={xai.provenance.operatingMode}
            />

            {/* Level 2: Calibrated Class Probabilities */}
            <ClassProbabilityBreakdown probabilities={xai.probabilities} />

            {/* Level 3: Geographic Centroid, FRP, Detections, Satellite */}
            <EventOverviewGrid event={event} />

            {/* Level 4: Nearby Industrial Assets & Proximity Intelligence */}
            <IndustrialAssetSection event={event} evidence={evidence} />

            {/* Level 4: Planck Dual-Band Thermal Pyrometry */}
            <PlanckPyrometrySection event={event} />

            {/* Level 4: 90-Day Historical Longitudinal Curve & Recurrence */}
            <HistoricalCurveSection event={event} />

            {/* Level 4: CAMEO-NIOSH Chemical Hazards */}
            <HazmatRiskCard event={event} evidence={evidence} />

            {/* Level 4: Grounded Explainable AI Evidence Signals */}
            <ExplainableAiSection
              event={event}
              evidence={evidence}
              intelligence={intelligence}
            />

            {/* Level 4: Operational Risk & Hazard Evaluation */}
            <div className="p-2.5 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-foreground-muted uppercase tracking-wider flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-accent" />
                  Operational Attention Level
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

              <div className="flex items-start gap-1 text-[8.5px] text-foreground-muted/80 leading-tight pt-1">
                <Info className="w-2.5 h-2.5 text-accent-cyan shrink-0 mt-0.5" />
                <span>{risk.disclaimer}</span>
              </div>
            </div>

            {/* Level 5: Emergency Response & Analyst-Confirmed Notification */}
            <EmergencyResponseSection event={event} evidence={evidence} />

            {/* Level 6: Model Provenance & Verification Lineage */}
            <ModelProvenanceCollapsible provenance={xai.provenance} />

            {/* Footer Provenance Stamp */}
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
          </>
        )}
      </div>

      {/* Tactical Incident Dossier Modal */}
      <TacticalDossierModal
        event={event}
        evidence={evidence}
        isOpen={isDossierModalOpen}
        onClose={() => setIsDossierModalOpen(false)}
      />
    </>
  );
}
