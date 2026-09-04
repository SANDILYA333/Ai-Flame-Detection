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
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-600/30 text-red-400 border border-red-500/50 animate-pulse">
            <Flame className="w-3 h-3 text-red-400" />
            ACTIVE FIRE
          </span>
        );
      case "CRITICAL":
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/40">
            <AlertTriangle className="w-3 h-3 text-red-400" />
            CRITICAL ({`<2 km`})
          </span>
        );
      case "WARNING":
      case "MODERATE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            WARNING (2-5 km)
          </span>
        );
      case "AWARENESS":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <Info className="w-3 h-3 text-blue-400" />
            AWARENESS (5-10 km)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            SAFE
          </span>
        );
    }
  };

  return (
    <div className={cn("flex flex-col h-full overflow-hidden bg-slate-950/90 text-slate-100", className)}>
      {/* Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 shadow-sm">
              <Trees className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold tracking-wide text-white flex items-center gap-2">
                Global Forest Threat Intelligence
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  LIVE
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Continuous real-time spatial evaluation against NASA FIRMS fire events
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadData(true)}
            disabled={isLoading || isRefreshing}
            className="h-8 px-2.5 bg-slate-800/50 hover:bg-slate-700/50 text-slate-300 border-slate-700"
          >
            <RotateCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin")} />
          </Button>
        </div>

        {/* Global Summary Stats Cards */}
        {summary && (
          <div className="grid grid-cols-5 gap-2 pt-1">
            <div
              onClick={() => setSelectedStatus("ALL")}
              className={cn(
                "p-2 rounded-lg border text-center cursor-pointer transition-all",
                selectedStatus === "ALL"
                  ? "bg-slate-800 border-slate-600 shadow"
                  : "bg-slate-900/60 border-slate-800/80 hover:bg-slate-850"
              )}
            >
              <div className="text-[10px] uppercase font-mono text-slate-400">Monitored</div>
              <div className="text-lg font-bold text-white mt-0.5">{summary.total_monitored_forests}</div>
            </div>
            <div
              onClick={() => setSelectedStatus("ACTIVE_FIRE")}
              className={cn(
                "p-2 rounded-lg border text-center cursor-pointer transition-all",
                selectedStatus === "ACTIVE_FIRE"
                  ? "bg-red-950/80 border-red-500 shadow-red-900/30"
                  : "bg-red-950/30 border-red-900/40 hover:bg-red-950/50"
              )}
            >
              <div className="text-[10px] uppercase font-mono text-red-300">Active Fire</div>
              <div className="text-lg font-bold text-red-400 mt-0.5 flex items-center justify-center gap-1">
                {summary.active_fire_forests > 0 && <Flame className="w-3.5 h-3.5 animate-pulse" />}
                {summary.active_fire_forests}
              </div>
            </div>
            <div
              onClick={() => setSelectedStatus("CRITICAL")}
              className={cn(
                "p-2 rounded-lg border text-center cursor-pointer transition-all",
                selectedStatus === "CRITICAL"
                  ? "bg-red-950/60 border-red-600 shadow"
                  : "bg-red-950/20 border-red-900/30 hover:bg-red-950/40"
              )}
            >
              <div className="text-[10px] uppercase font-mono text-red-300">Critical</div>
              <div className="text-lg font-bold text-red-400 mt-0.5">{summary.critical_forests}</div>
            </div>
            <div
              onClick={() => setSelectedStatus("WARNING")}
              className={cn(
                "p-2 rounded-lg border text-center cursor-pointer transition-all",
                selectedStatus === "WARNING"
                  ? "bg-amber-950/60 border-amber-500 shadow"
                  : "bg-amber-950/20 border-amber-900/30 hover:bg-amber-950/40"
              )}
            >
              <div className="text-[10px] uppercase font-mono text-amber-300">Warning</div>
              <div className="text-lg font-bold text-amber-400 mt-0.5">{summary.warning_forests}</div>
            </div>
            <div
              onClick={() => setSelectedStatus("SAFE")}
              className={cn(
                "p-2 rounded-lg border text-center cursor-pointer transition-all",
                selectedStatus === "SAFE"
                  ? "bg-emerald-950/60 border-emerald-500 shadow"
                  : "bg-emerald-950/20 border-emerald-900/30 hover:bg-emerald-950/40"
              )}
            >
              <div className="text-[10px] uppercase font-mono text-emerald-300">Safe</div>
              <div className="text-lg font-bold text-emerald-400 mt-0.5">{summary.safe_forests}</div>
            </div>
          </div>
        )}

        {/* Demo Runner Bar */}
        <div className="mt-3 p-2.5 rounded-lg bg-gradient-to-r from-slate-900 via-emerald-950/30 to-slate-900 border border-emerald-800/40 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-emerald-300 font-medium">
              <Play className="w-3.5 h-3.5 text-emerald-400" />
              <span>Deterministic Escalation Simulation Demo</span>
            </div>
            <Button
              size="sm"
              onClick={runEscalationDemo}
              disabled={isDemoRunning}
              className="h-7 px-3 bg-accent hover:bg-accent/90 text-bg-base text-xs font-bold shadow-sm transition-all"
            >
              {isDemoRunning ? (
                <span className="flex items-center gap-1.5">
                  <RotateCw className="w-3 h-3 animate-spin" /> Step {demoStep}/4...
                </span>
              ) : (
                "Run Fire Escalation Demo"
              )}
            </Button>
          </div>

          {demoStatusLog.length > 0 && (
            <div className="text-[11px] font-mono text-slate-300 bg-black/40 p-2 rounded border border-slate-800/80 max-h-20 overflow-y-auto space-y-1">
              {demoStatusLog.map((log, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-emerald-400">
                  <span className="text-slate-500">›</span>
                  <span>{log}</span>
                </div>
              ))}
            </div>
          )}

          {activeSimAlert && (
            <div className="p-2 rounded bg-red-950/40 border border-red-800/60 flex items-center justify-between text-xs text-red-200 animate-in fade-in duration-300">
              <div className="flex items-center gap-2">
                <BellRing className="w-4 h-4 text-red-400 animate-bounce" />
                <span>
                  Alert Dispatched: <strong>{activeSimAlert.alert_id}</strong> (SMS & WhatsApp Delivered)
                </span>
              </div>
              <span className="font-mono text-[10px] text-red-300 bg-red-900/60 px-1.5 py-0.5 rounded">
                DELIVERED
              </span>
            </div>
          )}
        </div>

        {/* Search & Filter bar */}
        <div className="mt-3 flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search forests by name, country, or OSM ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-xs bg-slate-900/80 border border-slate-700/70 rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>
          {searchQuery && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSearchQuery("")}
              className="h-8 px-2 text-xs text-slate-400 hover:text-white"
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Forest Threat List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 divide-y divide-slate-800/50">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs gap-2">
            <RotateCw className="w-5 h-5 animate-spin text-emerald-400" />
            <span>Evaluating spatial forest intelligence...</span>
          </div>
        ) : forests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs text-center p-4">
            <Trees className="w-8 h-8 text-slate-600 mb-2" />
            <span className="font-medium text-slate-300">No forests matching query</span>
            <span className="text-[11px] text-slate-500 mt-1">
              Try adjusting search terms or threat status filters
            </span>
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
                  "p-3 rounded-xl border transition-all cursor-pointer group pt-3",
                  isThreatened
                    ? forest.threat_level === "ACTIVE_FIRE" || forest.threat_level === "INSIDE_FOREST"
                      ? "bg-red-950/20 border-red-700/50 hover:bg-red-950/40 hover:border-red-500 shadow-sm"
                      : forest.threat_level === "CRITICAL"
                      ? "bg-red-950/15 border-red-800/40 hover:bg-red-950/30 hover:border-red-600 shadow-sm"
                      : forest.threat_level === "WARNING"
                      ? "bg-amber-950/15 border-amber-800/40 hover:bg-amber-950/30 hover:border-amber-600 shadow-sm"
                      : "bg-blue-950/15 border-blue-800/40 hover:bg-blue-950/30 hover:border-blue-600 shadow-sm"
                    : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/60 hover:border-slate-700"
                )}
              >
                {/* Forest header row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-white truncate group-hover:text-emerald-300 transition-colors">
                        {forest.name || "Monitored Forest Area"}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {forest.country_code}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                      <span>{forest.forest_type}</span>
                      <span>•</span>
                      <span>{forest.area_km2.toFixed(1)} km²</span>
                      <span>•</span>
                      <span className="font-mono text-[10px] text-slate-500">{forest.osm_identity}</span>
                    </div>
                  </div>
                  <div>{getThreatBadge(forest.threat_level)}</div>
                </div>

                {/* Threat Telemetry Row */}
                {isThreatened && (
                  <div className="mt-2.5 p-2 rounded-lg bg-black/40 border border-slate-800/80 text-xs flex flex-col gap-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1 text-slate-300">
                        <Flame className="w-3.5 h-3.5 text-amber-400" />
                        <span>
                          Nearest Fire:{" "}
                          <strong className="text-white">
                            {forest.inside_forest
                              ? "INSIDE (0.0 km)"
                              : `${forest.primary_distance_km?.toFixed(2)} km`}
                          </strong>
                        </span>
                      </div>
                      {forest.primary_frp_mw !== null && forest.primary_frp_mw !== undefined && (
                        <span className="text-slate-400 font-mono">
                          FRP: <strong className="text-amber-300">{forest.primary_frp_mw.toFixed(1)} MW</strong>
                        </span>
                      )}
                    </div>

                    {/* Grounded Why-at-risk bullets */}
                    {forest.why_at_risk && forest.why_at_risk.length > 0 && (
                      <div className="space-y-0.5 pt-1 border-t border-slate-800/60">
                        {forest.why_at_risk.slice(0, 2).map((bullet, bIdx) => (
                          <div key={bIdx} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                            <span className="text-emerald-400 mt-0.5">›</span>
                            <span>{bullet}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Footer action row */}
                <div className="mt-2.5 flex items-center justify-between pt-1 border-t border-slate-800/40 text-[11px] text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3 h-3 text-slate-500" />
                    <span>
                      {forest.centroid.latitude.toFixed(3)}°, {forest.centroid.longitude.toFixed(3)}°
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-emerald-400 group-hover:translate-x-0.5 transition-transform font-medium">
                    <span>Inspect Threat Intelligence</span>
                    <ChevronRight className="w-3.5 h-3.5" />
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
