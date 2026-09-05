"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Trees,
  Flame,
  AlertTriangle,
  ShieldCheck,
  Search,
  RotateCw,
  Eye,
  BellRing,
  Play,
  CheckCircle2,
  TrendingUp,
  MapPin,
  ExternalLink,
  ChevronRight,
  Info,
} from "lucide-react";
import {
  fetchForestMonitoringDashboard,
  ForestThreatSummaryItem,
  GlobalForestMonitoringSummary,
  dispatchForestProximityAlert,
} from "@/lib/api/forests";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface GlobalForestMonitoringHubProps {
  onSelectForest?: (forestId: string, centroid?: { latitude: number; longitude: number }) => void;
  onOpenForestDetail?: (forestId: string) => void;
  className?: string;
}

export function GlobalForestMonitoringHub({
  onSelectForest,
  onOpenForestDetail,
  className,
}: GlobalForestMonitoringHubProps) {
  const [summary, setSummary] = useState<GlobalForestMonitoringSummary | null>(null);
  const [forests, setForests] = useState<ForestThreatSummaryItem[]>([]);
  const [totalFiltered, setTotalFiltered] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Demo simulation state
  const [isDemoRunning, setIsDemoRunning] = useState<boolean>(false);
  const [demoStep, setDemoStep] = useState<number>(0);
  const [demoStatusLog, setDemoStatusLog] = useState<string[]>([]);
  const [activeSimAlert, setActiveSimAlert] = useState<any | null>(null);

  const loadData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    try {
      const res = await fetchForestMonitoringDashboard({
        status: selectedStatus === "ALL" ? undefined : selectedStatus,
        search: searchQuery.trim() || undefined,
        limit: 100,
      });
      if (res && res.success) {
        setSummary(res.summary);
        setForests(res.forests);
        setTotalFiltered(res.total_filtered);
      }
    } catch (err) {
      console.error("Failed to load forest monitoring dashboard:", err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedStatus, searchQuery]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Run 4-step deterministic simulation demo
  const runEscalationDemo = async () => {
    if (isDemoRunning) return;
    setIsDemoRunning(true);
    setDemoStep(1);
    setDemoStatusLog(["Initiating Step 1: Fire detected approaching Gir Forest (AWARENESS ~8.5 km)..."]);

    try {
      // Step 1: Awareness
      await new Promise((r) => setTimeout(r, 1200));
      setDemoStep(2);
      setDemoStatusLog((prev) => [
        "Step 2: Fire advances within WARNING threshold (4.2 km). Proximity alert queued.",
        ...prev,
      ]);

      // Step 2 -> Step 3: Critical Alert Dispatch
      await new Promise((r) => setTimeout(r, 1500));
      setDemoStep(3);
      setDemoStatusLog((prev) => [
        "Step 3: Escalation to CRITICAL (1.2 km)! Multi-channel automated SMS & WhatsApp notification triggered to Forest Ranger unit.",
        ...prev,
      ]);

      // Dispatch real simulated alert via backend API
      const targetForest = forests[0]?.forest_id || "forest_way_24680";
      const targetEvent = forests[0]?.primary_event_id || "evt_jamnagar_flaring_001";

      const alertRes = await dispatchForestProximityAlert({
        event_id: targetEvent,
        forest_id: targetForest,
        fire_confidence: 98.5,
        recipient_phone: "+91-9876543210",
        channels: ["sms", "whatsapp"],
        force_dispatch: true,
      });

      if (alertRes && alertRes.success) {
        setActiveSimAlert(alertRes);
      }

      // Step 4: Active fire inside boundary
      await new Promise((r) => setTimeout(r, 1800));
      setDemoStep(4);
      setDemoStatusLog((prev) => [
        "Step 4: ACTIVE FIRE (0.0 km) inside forest perimeter! Full emergency perimeter protocol dispatched.",
        ...prev,
      ]);
      await loadData();
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setIsDemoRunning(false);
    }
  };

  const getThreatBadge = (level: string) => {
    switch (level) {
      case "ACTIVE_FIRE":
      case "INSIDE_FOREST":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-state-error/25 text-state-error border border-state-error/50 animate-pulse font-mono shrink-0">
            <Flame className="w-3 h-3 text-state-error" />
            ACTIVE FIRE
          </span>
        );
      case "CRITICAL":
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-state-error/20 text-state-error border border-state-error/40 font-mono shrink-0">
            <AlertTriangle className="w-3 h-3 text-state-error" />
            CRITICAL (&lt;2 km)
          </span>
        );
      case "WARNING":
      case "MODERATE":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-state-warning/20 text-state-warning border border-state-warning/40 font-mono shrink-0">
            <AlertTriangle className="w-3 h-3 text-state-warning" />
            WARNING (2-5 km)
          </span>
        );
      case "AWARENESS":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 font-mono shrink-0">
            <Info className="w-3 h-3 text-accent-cyan" />
            AWARENESS (5-10 km)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-mono shrink-0">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            SAFE
          </span>
        );
    }
  };

  return (
    <div className={cn("flex flex-col h-full overflow-hidden text-foreground", className)}>
      {/* 1. Header with System Title, LIVE Indicator & Refresh Trigger */}
      <div className="flex items-start justify-between border-b border-border/80 pb-2.5 mb-2.5">
        <div className="flex items-start gap-2 min-w-0">
          <div className="w-7 h-7 rounded-control bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
            <Trees className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <h2 className="text-xs font-bold text-foreground tracking-tight">
                Global Forest Threat Intelligence
              </h2>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[9px] font-mono font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE
              </span>
            </div>
            <p className="text-[10px] text-foreground-muted mt-0.5 leading-snug">
              Continuous real-time spatial evaluation against NASA FIRMS fire events
            </p>
          </div>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={isLoading || isRefreshing}
          title="Refresh forest threat intelligence"
          className="p-1.5 rounded-control bg-surface hover:bg-surface-raised border border-border text-foreground-muted hover:text-foreground transition-colors disabled:opacity-50 shrink-0"
        >
          <RotateCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin text-emerald-400")} />
        </button>
      </div>

      {/* 2. Global Summary Stats Quick Filters */}
      {summary && (
        <div className="grid grid-cols-5 gap-1 mb-2.5">
          {/* Monitored / ALL */}
          <button
            onClick={() => setSelectedStatus("ALL")}
            className={cn(
              "p-1.5 rounded border text-center transition-all flex flex-col justify-between items-center min-h-[46px]",
              selectedStatus === "ALL"
                ? "bg-foreground/15 border-foreground/40 text-foreground font-bold shadow-sm ring-1 ring-foreground/30"
                : "bg-surface/70 border-border text-foreground-muted hover:text-foreground hover:bg-surface-hover"
            )}
          >
            <div className="text-[8.5px] uppercase font-mono tracking-wider text-foreground-muted">Monitored</div>
            <div className="text-sm font-bold font-mono text-foreground">{summary.total_monitored_forests}</div>
          </button>

          {/* Active Fire */}
          <button
            onClick={() => setSelectedStatus(selectedStatus === "ACTIVE_FIRE" ? "ALL" : "ACTIVE_FIRE")}
            className={cn(
              "p-1.5 rounded border text-center transition-all flex flex-col justify-between items-center min-h-[46px]",
              selectedStatus === "ACTIVE_FIRE"
                ? "bg-state-error/25 border-state-error text-state-error font-bold shadow-sm ring-1 ring-state-error/50"
                : "bg-surface/70 border-border text-state-error hover:bg-state-error/15"
            )}
          >
            <div className="text-[8.5px] uppercase font-mono tracking-wider text-red-400">Active Fire</div>
            <div className="text-sm font-bold font-mono text-red-400 flex items-center justify-center gap-0.5">
              {summary.active_fire_forests > 0 && <Flame className="w-3 h-3 text-red-400 animate-pulse" />}
              {summary.active_fire_forests}
            </div>
          </button>

          {/* Critical */}
          <button
            onClick={() => setSelectedStatus(selectedStatus === "CRITICAL" ? "ALL" : "CRITICAL")}
            className={cn(
              "p-1.5 rounded border text-center transition-all flex flex-col justify-between items-center min-h-[46px]",
              selectedStatus === "CRITICAL"
                ? "bg-state-error/20 border-red-500 text-red-400 font-bold shadow-sm ring-1 ring-red-500/50"
                : "bg-surface/70 border-border text-red-400/90 hover:bg-state-error/15"
            )}
          >
            <div className="text-[8.5px] uppercase font-mono tracking-wider text-red-400">Critical</div>
            <div className="text-sm font-bold font-mono text-red-400">{summary.critical_forests}</div>
          </button>

          {/* Warning */}
          <button
            onClick={() => setSelectedStatus(selectedStatus === "WARNING" ? "ALL" : "WARNING")}
            className={cn(
              "p-1.5 rounded border text-center transition-all flex flex-col justify-between items-center min-h-[46px]",
              selectedStatus === "WARNING"
                ? "bg-state-warning/25 border-state-warning text-state-warning font-bold shadow-sm ring-1 ring-state-warning/50"
                : "bg-surface/70 border-border text-state-warning hover:bg-state-warning/15"
            )}
          >
            <div className="text-[8.5px] uppercase font-mono tracking-wider text-amber-400">Warning</div>
            <div className="text-sm font-bold font-mono text-amber-400">{summary.warning_forests}</div>
          </button>

          {/* Safe */}
          <button
            onClick={() => setSelectedStatus(selectedStatus === "SAFE" ? "ALL" : "SAFE")}
            className={cn(
              "p-1.5 rounded border text-center transition-all flex flex-col justify-between items-center min-h-[46px]",
              selectedStatus === "SAFE"
                ? "bg-emerald-500/20 border-emerald-500 text-emerald-400 font-bold shadow-sm ring-1 ring-emerald-500/50"
                : "bg-surface/70 border-border text-emerald-400 hover:bg-emerald-500/15"
            )}
          >
            <div className="text-[8.5px] uppercase font-mono tracking-wider text-emerald-400">Safe</div>
            <div className="text-sm font-bold font-mono text-emerald-400">{summary.safe_forests}</div>
          </button>
        </div>
      )}

      {/* 3. Deterministic Escalation Simulation Demo Box */}
      <div className="mb-2.5 p-2 rounded-control bg-surface/80 border border-emerald-500/30 flex flex-col gap-2 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <Play className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-[11px] font-semibold text-emerald-300 truncate">
              Deterministic Escalation Demo
            </span>
          </div>
          <button
            onClick={runEscalationDemo}
            disabled={isDemoRunning}
            className="px-2.5 py-1 rounded-control bg-accent hover:bg-emerald-400 text-background text-[10px] font-bold shadow-sm transition-all flex items-center gap-1.5 shrink-0 whitespace-nowrap cursor-pointer disabled:opacity-60"
          >
            {isDemoRunning ? (
              <>
                <RotateCw className="w-3 h-3 animate-spin text-background" />
                <span>STEP {demoStep}/4...</span>
              </>
            ) : (
              <span>RUN FIRE ESCALATION DEMO</span>
            )}
          </button>
        </div>

        {demoStatusLog.length > 0 && (
          <div className="text-[10px] font-mono text-foreground-secondary bg-background/90 p-2 rounded border border-border max-h-20 overflow-y-auto space-y-1">
            {demoStatusLog.map((log, idx) => (
              <div key={idx} className="flex items-start gap-1.5 text-emerald-400">
                <span className="text-foreground-muted">›</span>
                <span className="leading-tight">{log}</span>
              </div>
            ))}
          </div>
        )}

        {activeSimAlert && (
          <div className="p-2 rounded bg-state-error/20 border border-state-error/50 flex items-center justify-between text-[11px] text-red-200 animate-in fade-in duration-300">
            <div className="flex items-center gap-1.5 min-w-0">
              <BellRing className="w-3.5 h-3.5 text-red-400 shrink-0 animate-bounce" />
              <span className="truncate">
                Alert: <strong className="text-red-100">{activeSimAlert.alert_id}</strong> (SMS & WhatsApp)
              </span>
            </div>
            <span className="font-mono text-[9px] font-bold text-red-300 bg-red-950 px-1.5 py-0.5 rounded border border-red-800 shrink-0">
              DELIVERED
            </span>
          </div>
        )}
      </div>

      {/* 4. Search & Filter Bar */}
      <div className="flex items-center gap-1.5 mb-2">
        <div className="relative flex-1">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-foreground-muted" />
          <input
            type="text"
            placeholder="Search forests by name, country..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-7 pl-6 pr-2 bg-background/70 border border-border rounded-control text-[11px] text-foreground placeholder:text-foreground-muted/60 focus:outline-none focus:border-accent font-mono transition-colors"
          />
        </div>
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="h-7 px-2 text-[10px] font-mono text-foreground-muted hover:text-foreground bg-surface border border-border rounded-control transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* 5. Forest Threat Stream */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[220px] max-h-[52vh] scrollbar-thin">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-48 text-foreground-muted text-xs gap-2">
            <RotateCw className="w-5 h-5 animate-spin text-emerald-400" />
            <span className="font-mono text-[11px]">Evaluating spatial forest intelligence...</span>
          </div>
        ) : forests.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-border/80 rounded-control bg-surface/30">
            <Trees className="w-6 h-6 text-foreground-muted mb-2" />
            <div className="text-xs font-semibold text-foreground">No Matching Forests</div>
            <div className="text-[10px] text-foreground-muted mt-1 max-w-[200px]">
              No monitored forests match the active search or threat filter.
            </div>
            {selectedStatus !== "ALL" && (
              <button
                onClick={() => setSelectedStatus("ALL")}
                className="mt-3 px-2.5 py-1 text-[10px] font-mono rounded-control bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/25 transition-colors"
              >
                Reset Filter
              </button>
            )}
          </div>
        ) : (
          forests.map((forest) => {
            const isThreatened = forest.threat_level !== "SAFE" && forest.threat_level !== "NONE";
            return (
              <div
                key={forest.forest_id}
                onClick={() => {
                  if (onSelectForest) {
                    onSelectForest(forest.forest_id, forest.centroid);
                  }
                  if (onOpenForestDetail) {
                    onOpenForestDetail(forest.forest_id);
                  }
                }}
                className={cn(
                  "p-2.5 rounded-control border transition-all cursor-pointer group select-none flex flex-col gap-1.5",
                  isThreatened
                    ? forest.threat_level === "ACTIVE_FIRE" || forest.threat_level === "INSIDE_FOREST"
                      ? "bg-state-error/10 border-state-error/40 hover:bg-state-error/20 hover:border-state-error shadow-sm"
                      : forest.threat_level === "CRITICAL"
                      ? "bg-state-error/5 border-state-error/30 hover:bg-state-error/15 hover:border-state-error/50 shadow-sm"
                      : forest.threat_level === "WARNING"
                      ? "bg-state-warning/5 border-state-warning/30 hover:bg-state-warning/15 hover:border-state-warning/50 shadow-sm"
                      : "bg-accent-cyan/5 border-accent-cyan/30 hover:bg-accent-cyan/15 hover:border-accent-cyan/50 shadow-sm"
                    : "bg-surface/60 border-border hover:bg-surface hover:border-border-strong"
                )}
              >
                {/* Forest Header Row */}
                <div className="flex items-start justify-between gap-1.5">
                  <div className="flex items-center gap-1.5 min-w-0 flex-1">
                    <span
                      className="font-semibold text-xs text-foreground truncate group-hover:text-accent transition-colors"
                      title={forest.name || "Monitored Forest Area"}
                    >
                      {forest.name || "Monitored Forest Area"}
                    </span>
                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-surface-raised text-foreground-secondary border border-border shrink-0">
                      {forest.country_code}
                    </span>
                  </div>
                  <div className="shrink-0">{getThreatBadge(forest.threat_level)}</div>
                </div>

                {/* Metadata Subtitle */}
                <div className="flex items-center gap-1.5 text-[10px] text-foreground-muted font-mono flex-wrap">
                  <span>{forest.forest_type}</span>
                  <span>•</span>
                  <span>{forest.area_km2.toFixed(1)} km²</span>
                  <span>•</span>
                  <span className="text-foreground-muted/70">{forest.osm_identity}</span>
                </div>

                {/* Threat Telemetry (if threatened) */}
                {isThreatened && (
                  <div className="p-2 rounded bg-background/80 border border-border text-[10px] font-mono flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1 text-foreground-secondary">
                        <Flame className="w-3 h-3 text-state-warning shrink-0" />
                        <span>
                          Nearest Fire:{" "}
                          <strong className="text-foreground">
                            {forest.inside_forest
                              ? "INSIDE (0.0 km)"
                              : `${forest.primary_distance_km?.toFixed(2)} km`}
                          </strong>
                        </span>
                      </div>
                      {forest.primary_frp_mw !== null && forest.primary_frp_mw !== undefined && (
                        <span className="text-foreground-muted">
                          FRP: <strong className="text-amber-400">{forest.primary_frp_mw.toFixed(1)} MW</strong>
                        </span>
                      )}
                    </div>

                    {/* Grounded Why-at-risk bullets */}
                    {forest.why_at_risk && forest.why_at_risk.length > 0 && (
                      <div className="space-y-0.5 pt-1 border-t border-border/60">
                        {forest.why_at_risk.slice(0, 2).map((bullet, bIdx) => (
                          <div key={bIdx} className="text-[10px] text-foreground-secondary flex items-start gap-1">
                            <span className="text-accent mt-0.5">›</span>
                            <span className="leading-tight">{bullet}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Footer Action Row */}
                <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[10px] text-foreground-muted font-mono">
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-foreground-muted/70 shrink-0" />
                    <span>
                      {forest.centroid.latitude.toFixed(3)}°, {forest.centroid.longitude.toFixed(3)}°
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-accent group-hover:translate-x-0.5 transition-transform font-semibold">
                    <span>Inspect Threat Intelligence</span>
                    <ChevronRight className="w-3 h-3" />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
