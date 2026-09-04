"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Trees,
  Flame,
  AlertTriangle,
  ShieldCheck,
  RotateCw,
  X,
  BellRing,
  ExternalLink,
  ChevronRight,
  MapPin,
  Send,
  PhoneCall,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import {
  fetchForestThreatDetail,
  ForestThreatDetailResponse,
  dispatchForestProximityAlert,
} from "@/lib/api/forests";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

export interface ForestThreatDetailDrawerProps {
  forestId: string | null;
  onClose: () => void;
  onNavigateToEvent?: (eventId: string) => void;
  className?: string;
}

export function ForestThreatDetailDrawer({
  forestId,
  onClose,
  onNavigateToEvent,
  className,
}: ForestThreatDetailDrawerProps) {
  const [detail, setDetail] = useState<ForestThreatDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [dispatchResult, setDispatchResult] = useState<any | null>(null);

  const loadDetail = useCallback(async () => {
    if (!forestId) return;
    setIsLoading(true);
    setDispatchResult(null);
    try {
      const res = await fetchForestThreatDetail(forestId);
      if (res && res.success) {
        setDetail(res);
      }
    } catch (err) {
      console.error("Failed to load forest threat detail:", err);
    } finally {
      setIsLoading(false);
    }
  }, [forestId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  if (!forestId) return null;

  const handleDispatchAlert = async () => {
    if (!detail) return;
    setIsDispatching(true);
    try {
      const primaryEvId = detail.nearest_event_id || detail.threatening_events[0]?.event_id || "evt_jamnagar_flaring_001";
      const res = await dispatchForestProximityAlert({
        event_id: primaryEvId,
        forest_id: detail.forest.id,
        fire_confidence: detail.primary_confidence || 95.0,
        recipient_phone: "+91-9876543210",
        channels: ["sms", "whatsapp"],
        force_dispatch: true,
      });
      if (res && res.success) {
        setDispatchResult(res);
      }
    } catch (err) {
      console.error("Alert dispatch failed:", err);
    } finally {
      setIsDispatching(false);
    }
  };

  const getThreatBadge = (level: string) => {
    switch (level) {
      case "ACTIVE_FIRE":
      case "INSIDE_FOREST":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-600/30 text-red-400 border border-red-500 animate-pulse">
            <Flame className="w-3.5 h-3.5 text-red-400" />
            ACTIVE FIRE INSIDE FOREST
          </span>
        );
      case "CRITICAL":
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            CRITICAL PROXIMITY ({`<2 km`})
          </span>
        );
      case "WARNING":
      case "MODERATE":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            WARNING PROXIMITY (2-5 km)
          </span>
        );
      case "AWARENESS":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            AWARENESS BUFFER (5-10 km)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            SAFE / PERIMETER CLEAR
          </span>
        );
    }
  };

  return (
    <div
      className={cn(
        "fixed inset-y-0 right-0 w-[480px] bg-slate-950/95 border-l border-slate-800 shadow-2xl backdrop-blur-xl z-50 flex flex-col text-slate-100 overflow-hidden animate-in slide-in-from-right duration-300",
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <Trees className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Forest Threat Intelligence</h3>
            <span className="text-[11px] font-mono text-slate-400">{forestId}</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-8 w-8 p-0 text-slate-400 hover:text-white hover:bg-slate-800"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-xs gap-2">
            <RotateCw className="w-6 h-6 animate-spin text-emerald-400" />
            <span>Evaluating geographic forest polygon...</span>
          </div>
        ) : !detail ? (
          <div className="text-center p-8 text-slate-400 text-xs">
            Failed to load threat details for this forest.
          </div>
        ) : (
          <>
            {/* Primary Status Card */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-base font-bold text-white">
                    {detail.forest.name || detail.forest.name_en || "Monitored Reserve"}
                  </h4>
                  <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                    <span>{detail.forest.region || detail.forest.country_code}</span>
                    <span>•</span>
                    <span>{detail.forest.forest_type}</span>
                    <span>•</span>
                    <span>{detail.forest.area_km2.toFixed(1)} km²</span>
                  </div>
                </div>
                <div>{getThreatBadge(detail.threat_level)}</div>
              </div>

              {/* Distance & Telemetry metrics */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
                <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Nearest Fire Distance</div>
                  <div className="text-sm font-bold text-white mt-0.5">
                    {detail.inside_forest
                      ? "0.0 km (INSIDE)"
                      : detail.nearest_distance_km !== null && detail.nearest_distance_km !== undefined
                      ? `${detail.nearest_distance_km.toFixed(2)} km`
                      : "No fire in range"}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Threat Progression</div>
                  <div className="text-sm font-bold text-amber-400 mt-0.5 font-mono">
                    {detail.progression_trend}
                  </div>
                </div>
              </div>
            </div>

            {/* Explainable AI Why-at-risk Section */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>Explainable Threat Assessment</span>
              </div>
              <div className="space-y-1.5">
                {detail.why_at_risk.map((bullet, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-slate-200">
                    <span className="text-emerald-400 mt-0.5 font-bold">›</span>
                    <span>{bullet}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Threatening Candidate Events */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                <span>Threatening Thermal Events ({detail.threatening_events.length})</span>
                <span className="text-[10px] text-slate-500 font-mono">Evaluated &lt; 10 km</span>
              </div>

              {detail.threatening_events.length === 0 ? (
                <div className="p-3 rounded-lg bg-slate-900/30 border border-slate-800 text-xs text-slate-400 text-center">
                  Zero active thermal events threatening this forest.
                </div>
              ) : (
                detail.threatening_events.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/90 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Flame className="w-3.5 h-3.5 text-amber-400" />
                        <span className="font-mono font-semibold text-white">{ev.event_id}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {ev.classification}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-2">
                        <span>
                          Dist:{" "}
                          <strong className="text-white">
                            {ev.inside_forest ? "0.0 km" : `${ev.distance_km.toFixed(2)} km`}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>FRP: {ev.frp_mw.toFixed(1)} MW</span>
                        <span>•</span>
                        <span>Conf: {ev.confidence.toFixed(0)}%</span>
                      </div>
                    </div>
                    {onNavigateToEvent && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onNavigateToEvent(ev.event_id)}
                        className="h-7 px-2 text-[11px] text-emerald-400 border-emerald-800/60 hover:bg-emerald-950/40"
                      >
                        Inspect Fire
                      </Button>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Emergency Alert Dispatch Action */}
            <div className="p-4 rounded-xl bg-gradient-to-b from-slate-900 to-red-950/30 border border-red-800/40 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-red-300">
                  <BellRing className="w-4 h-4 text-red-400 animate-pulse" />
                  <span>Emergency Responder Dispatch</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">Multi-Channel Simulated</span>
              </div>

              <p className="text-[11px] text-slate-300">
                Trigger high-priority simulated SMS & WhatsApp emergency broadcast to forest ranger post and local firefighting teams.
              </p>

              <Button
                onClick={handleDispatchAlert}
                disabled={isDispatching}
                className="w-full h-9 bg-red-600 hover:bg-red-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-red-900/30 transition-all"
              >
                {isDispatching ? (
                  <>
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Dispatching Emergency Dispatch...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Dispatch Ranger Proximity Alert</span>
                  </>
                )}
              </Button>

              {dispatchResult && (
                <div className="p-2.5 rounded-lg bg-black/60 border border-emerald-500/50 text-xs text-emerald-300 flex flex-col gap-1 font-mono">
                  <div className="flex items-center justify-between">
                    <span>Alert Ref: {dispatchResult.alert_id}</span>
                    <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 text-[10px]">
                      DELIVERED
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Escalation: {dispatchResult.is_escalation ? "YES" : "NO"} • Distance: {dispatchResult.distance_km.toFixed(2)} km
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
