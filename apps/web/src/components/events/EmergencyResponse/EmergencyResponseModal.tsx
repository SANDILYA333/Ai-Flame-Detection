"use client";

import React, { useEffect } from "react";
import type { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import { EmergencyResponseSection } from "./EmergencyResponseSection";
import { Siren, X, Crosshair, Flame, ShieldAlert, Cpu } from "lucide-react";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatFrp, formatPercent } from "@/lib/format/numbers";
import { cn } from "@/lib/utils";

export interface EmergencyResponseModalProps {
  isOpen: boolean;
  event: ThermalEvent | null;
  evidence?: EventEvidenceResponse | null;
  onClose: () => void;
  className?: string;
}

export function EmergencyResponseModal({
  isOpen,
  event,
  evidence,
  onClose,
  className,
}: EmergencyResponseModalProps) {
  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !event) return null;

  const lat = event.latitude;
  const lon = event.longitude;
  const confidencePercent = event.confidence ? event.confidence * 100 : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-background/85 backdrop-blur-md animate-in fade-in duration-150 select-none overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="response-center-title"
    >
      <div
        className={cn(
          "w-full max-w-4xl max-h-[92vh] bg-surface-raised border border-border rounded-panel shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 font-mono text-xs",
          className
        )}
      >
        {/* Header Bar */}
        <div className="p-3.5 sm:p-4 bg-surface/90 border-b border-border flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-control bg-state-error/15 border border-state-error/30 flex items-center justify-center text-state-error shrink-0">
              <Siren className="w-4 h-4 animate-pulse-subtle" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2
                  id="response-center-title"
                  className="text-xs sm:text-sm font-bold text-foreground uppercase tracking-wider truncate"
                >
                  EMERGENCY RESPONSE & DISPATCH CENTER
                </h2>
                <span className="px-1.5 py-0.2 rounded bg-state-error/10 text-state-error border border-state-error/20 text-[9px] font-bold">
                  OPERATIONAL
                </span>
              </div>
              <div className="text-[10px] text-foreground-muted flex items-center gap-2 flex-wrap">
                <span className="text-accent font-semibold">{event.event_id}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Crosshair className="w-2.5 h-2.5 text-accent-cyan" />
                  {formatCoordinate(lat, lon)}
                </span>
                {event.frp_mw > 0 && (
                  <>
                    <span>•</span>
                    <span className="flex items-center gap-1 text-accent">
                      <Flame className="w-2.5 h-2.5" />
                      {formatFrp(event.frp_mw)}
                    </span>
                  </>
                )}
                {confidencePercent !== null && (
                  <>
                    <span>•</span>
                    <span className="text-foreground-secondary">
                      Conf: {confidencePercent.toFixed(1)}%
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            title="Close Emergency Response Center (Esc)"
            aria-label="Close Emergency Response Center"
            className="p-1.5 text-foreground-muted hover:text-foreground rounded-control hover:bg-surface border border-transparent hover:border-border transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Response Center Content */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4 scrollbar-thin">
          <EmergencyResponseSection
            event={event}
            evidence={evidence}
            className="border-0 bg-transparent p-0"
          />
        </div>

        {/* Footer info bar */}
        <div className="p-2 sm:px-4 bg-surface/80 border-t border-border/60 flex items-center justify-between text-[9.5px] text-foreground-muted shrink-0">
          <div className="flex items-center gap-1.5 truncate">
            <Cpu className="w-3 h-3 text-accent shrink-0" />
            <span>Authoritative Geospatial Proximity & Policy Execution Subsystem</span>
          </div>
          <span className="text-[8.5px] text-foreground-muted/80">
            Press <kbd className="px-1 py-0.5 rounded bg-surface border border-border">Esc</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}
