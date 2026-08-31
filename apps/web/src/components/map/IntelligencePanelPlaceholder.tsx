"use client";

import React, { useMemo } from "react";
import { Activity, Flame, Factory, AlertTriangle, HelpCircle, Cpu, Clock, CheckCircle2, Trees, BarChart2 } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { Badge } from "@/components/ui/Badge";
import { Divider } from "@/components/ui/Divider";
import { ThermalEvent } from "@/types/event";
import { APP_CONFIG } from "@/config/ui";
import { formatFrp } from "@/lib/format/numbers";
import { formatCoordinate } from "@/lib/format/coordinates";
import { cn } from "@/lib/utils";

export interface IntelligencePanelProps {
  events?: ThermalEvent[];
  selectedEvent?: ThermalEvent | null;
  onSelectEvent?: (event: ThermalEvent) => void;
  onClose?: () => void;
  className?: string;
}

export function IntelligencePanelPlaceholder({
  events = [],
  selectedEvent,
  onSelectEvent,
  onClose,
  className,
}: IntelligencePanelProps) {
  // Compute live aggregate stats
  const stats = useMemo(() => {
    const total = events.length;
    let industrial = 0;
    let nonIndustrial = 0;
    let unknown = 0;
    let reviewRequired = 0;
    let maxFrp = 0;

    events.forEach((evt) => {
      if (evt.classification === "INDUSTRIAL") industrial++;
      else if (evt.classification === "NON_INDUSTRIAL") nonIndustrial++;
      else unknown++;

      if (evt.uncertainty_state === "REVIEW_REQUIRED") reviewRequired++;
      if (evt.frp_mw > maxFrp) maxFrp = evt.frp_mw;
    });

    return { total, industrial, nonIndustrial, unknown, reviewRequired, maxFrp };
  }, [events]);

  return (
    <Panel
      variant="glass"
      className={cn("w-88 max-h-[85vh] overflow-y-auto flex flex-col p-3 shadow-panel select-none", className)}
    >
      <PanelHeader
        title="Thermal Intelligence"
        subtitle="Real-Time Classification Stream"
        icon={<Activity className="w-4 h-4 text-accent" />}
        onClose={onClose}
      />

      {/* Summary KPI grid with dynamic values */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-surface-raised p-2.5 rounded-control border border-border">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-foreground-muted font-mono uppercase">Active Events</span>
            <Flame className="w-3.5 h-3.5 text-thermal-primary animate-flame" />
          </div>
          <div className="text-xl font-mono font-bold text-foreground mt-1">{stats.total}</div>
          <div className="text-[9px] text-accent font-mono mt-0.5 flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> Clustered WGS84
          </div>
        </div>

        <div className="bg-surface-raised p-2.5 rounded-control border border-border">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-foreground-muted font-mono uppercase">Industrial</span>
            <Factory className="w-3.5 h-3.5 text-accent" />
          </div>
          <div className="text-xl font-mono font-bold text-accent mt-1">{stats.industrial}</div>
          <div className="text-[9px] text-foreground-muted font-mono mt-0.5">High Confidence</div>
        </div>

        <div className="bg-surface-raised p-2.5 rounded-control border border-border">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-foreground-muted font-mono uppercase">Review Req.</span>
            <AlertTriangle className="w-3.5 h-3.5 text-state-warning" />
          </div>
          <div className="text-xl font-mono font-bold text-state-warning mt-1">{stats.reviewRequired}</div>
          <div className="text-[9px] text-state-warning font-mono mt-0.5">Uncertainty Flag</div>
        </div>

        <div className="bg-surface-raised p-2.5 rounded-control border border-border">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-foreground-muted font-mono uppercase">Unknown / Amb.</span>
            <HelpCircle className="w-3.5 h-3.5 text-accent-cyan" />
          </div>
          <div className="text-xl font-mono font-bold text-accent-cyan mt-1">{stats.unknown}</div>
          <div className="text-[9px] text-foreground-muted font-mono mt-0.5">Awaiting Context</div>
        </div>
      </div>

      <Divider />

      {/* Featured / Active Telemetry Event */}
      <div className="mb-3">
        <div className="text-[10px] uppercase font-mono tracking-wider text-foreground-muted mb-2 flex items-center justify-between">
          <span>{selectedEvent ? "Selected Focus" : "Max Intensity Cluster"}</span>
          <Badge variant="thermal" size="sm">
            Peak: {formatFrp(selectedEvent ? selectedEvent.frp_mw : stats.maxFrp)}
          </Badge>
        </div>

        {events.length > 0 && (
          <div
            onClick={() => onSelectEvent && onSelectEvent(selectedEvent || events[0])}
            className="p-2.5 rounded-control bg-surface-raised/80 border border-border/80 space-y-1.5 cursor-pointer hover:border-accent transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-foreground">
                {(selectedEvent || events[0]).event_id}
              </span>
              <Badge
                variant={
                  (selectedEvent || events[0]).classification === "INDUSTRIAL"
                    ? "industrial"
                    : (selectedEvent || events[0]).classification === "UNKNOWN"
                    ? "neutral"
                    : "warning"
                }
                size="sm"
              >
                {(selectedEvent || events[0]).classification}
              </Badge>
            </div>
            <div className="text-[11px] text-foreground-secondary font-mono">
              {formatCoordinate(
                (selectedEvent || events[0]).latitude,
                (selectedEvent || events[0]).longitude
              )}
            </div>
            <div className="text-[10px] text-foreground-muted font-mono flex items-center justify-between pt-1 border-t border-border/50">
              <span>
                Confidence: <strong className="text-accent">{((selectedEvent || events[0]).confidence * 100).toFixed(1)}%</strong>
              </span>
              <span>{(selectedEvent || events[0]).detection_count} detections</span>
            </div>
          </div>
        )}
      </div>

      {/* Model Provenance */}
      <div className="mt-auto pt-2 border-t border-border/60 text-[10px] font-mono text-foreground-muted space-y-1">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3 h-3 text-accent-cyan" /> Model
          </span>
          <span className="text-foreground">{APP_CONFIG.modelName}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-foreground-muted" /> Schema
          </span>
          <span className="text-foreground-secondary">{APP_CONFIG.featureSchema}</span>
        </div>
      </div>
    </Panel>
  );
}
