"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import type { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import type {
  EmergencyResponder,
  EventResponseRecommendation,
  ResponseActivityRecord,
  NotificationAction,
  NotificationChannel,
} from "@/types/responders";
import {
  fetchEventResponders,
  postNotifyResponder,
  fetchResponseActivity,
} from "@/lib/responders/api";
import { NotificationConfirmModal } from "./NotificationConfirmModal";
import { ResponseActivityFeed } from "./ResponseActivityFeed";
import {
  Siren,
  Flame,
  ShieldAlert,
  Clock,
  Building2,
  Phone,
  Send,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
  Smartphone,
  MessageSquare,
  Sparkles,
  Save,
  RotateCw,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmergencyResponseSectionProps {
  event: ThermalEvent;
  evidence?: EventEvidenceResponse | null;
  className?: string;
}

export function EmergencyResponseSection({
  event,
  evidence,
  className,
}: EmergencyResponseSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [recommendation, setRecommendation] =
    useState<EventResponseRecommendation | null>(null);
  const [activity, setActivity] = useState<ResponseActivityRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Demo Phone Number Configuration State
  const [demoPhone, setDemoPhone] = useState<string>("+91 9876543210");
  const [phoneInput, setPhoneInput] = useState<string>("+91 9876543210");
  const [phoneSavedFeedback, setPhoneSavedFeedback] = useState(false);

  // Load demo phone from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("flame_demo_phone");
      if (saved) {
        setDemoPhone(saved);
        setPhoneInput(saved);
      }
    } catch {
      // LocalStorage unavailable
    }
  }, []);

  const handleApplyPhone = () => {
    const cleaned = phoneInput.trim();
    if (cleaned) {
      setDemoPhone(cleaned);
      try {
        localStorage.setItem("flame_demo_phone", cleaned);
      } catch {
        // LocalStorage unavailable
      }
      setPhoneSavedFeedback(true);
      setTimeout(() => setPhoneSavedFeedback(false), 2500);
    }
  };

  // Selected responder for confirmation modal
  const [confirmModalState, setConfirmModalState] = useState<{
    isOpen: boolean;
    responder: EmergencyResponder | null;
    action: NotificationAction;
  }>({
    isOpen: false,
    responder: null,
    action: "NOTIFY",
  });

  // Feedback toast state
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setIsError(false);
    setErrorMessage(null);

    try {
      const [rec, act] = await Promise.all([
        fetchEventResponders(event, demoPhone),
        fetchResponseActivity(event.event_id),
      ]);
      setRecommendation(rec);
      setActivity(act);
    } catch (err: any) {
      setIsError(true);
      setErrorMessage(err?.message || "Failed to load response intelligence.");
    } finally {
      setIsLoading(false);
    }
  }, [event, demoPhone]);

  // Load recommendations & activity whenever event or applied demoPhone changes
  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenConfirm = (
    responder: EmergencyResponder,
    action: NotificationAction
  ) => {
    setConfirmModalState({
      isOpen: true,
      responder,
      action,
    });
  };

  const handleConfirmNotification = async (
    notes?: string,
    channels?: NotificationChannel[]
  ) => {
    if (!confirmModalState.responder) return;
    const resp = confirmModalState.responder;
    const action = confirmModalState.action;

    try {
      const escalationType =
        recommendation?.escalation_type ||
        (recommendation?.auto_escalation_eligible
          ? "HIGH_CONFIDENCE_AUTO"
          : recommendation?.response_priority === "CRITICAL"
          ? "CRITICAL_MEDICAL"
          : "ADMIN_CONFIRMED");

      const targetChannels = channels && channels.length > 0
        ? channels
        : ["SMS", "WHATSAPP"];

      const result = await postNotifyResponder(
        event.event_id,
        {
          responder_id: resp.id,
          action,
          mode: "SIMULATED",
          recipient_phone: demoPhone,
          channels: targetChannels as ("SMS" | "WHATSAPP")[],
          escalation_type: escalationType,
          analyst_notes: notes,
        },
        resp.name,
        resp.type
      );

      // Refresh activity list from backend
      const updatedActivity = await fetchResponseActivity(event.event_id);
      setActivity(updatedActivity);

      setFeedbackMessage(
        result.message || "Notification has been sent successfully"
      );
      setTimeout(() => setFeedbackMessage(null), 5000);
    } catch (err: any) {
      console.error("Failed to submit notification:", err);
      setFeedbackMessage(err?.message || "Notification could not be sent.");
      setTimeout(() => setFeedbackMessage(null), 5000);
    }
  };

  const confidencePercent = useMemo(() => {
    const raw = recommendation?.confidence ?? event.confidence ?? 0.85;
    return raw <= 1.0 ? raw * 100 : raw;
  }, [recommendation, event]);

  const priorityStyles = useMemo(() => {
    if (!recommendation) {
      return {
        bg: "bg-surface",
        text: "text-foreground",
        border: "border-border",
      };
    }
    switch (recommendation.response_priority) {
      case "CRITICAL":
        return {
          bg: "bg-state-error/15",
          text: "text-state-error",
          border: "border-state-error/30",
        };
      case "HIGH":
        return {
          bg: "bg-accent/15",
          text: "text-accent",
          border: "border-accent/30",
        };
      case "MONITOR_ONLY":
        return {
          bg: "bg-state-success/15",
          text: "text-state-success",
          border: "border-state-success/30",
        };
      case "REVIEW_REQUIRED":
        return {
          bg: "bg-state-warning/15",
          text: "text-state-warning",
          border: "border-state-warning/30",
        };
      default:
        return {
          bg: "bg-accent-cyan/15",
          text: "text-accent-cyan",
          border: "border-accent-cyan/30",
        };
    }
  }, [recommendation]);

  // Extract nearest 2 hospitals and nearest 2 fire stations
  const nearestHospitals = useMemo(() => {
    if (
      recommendation?.nearest_hospitals &&
      recommendation.nearest_hospitals.length > 0
    ) {
      return recommendation.nearest_hospitals.slice(0, 2);
    }
    return (recommendation?.responders || [])
      .filter((r) => r.type === "BURN_ICU" || r.type === "HOSPITAL" || r.type === "BURN_INTENSIVE_CARE_HOSPITAL")
      .slice(0, 2);
  }, [recommendation]);

  const nearestFireStations = useMemo(() => {
    if (
      recommendation?.nearest_fire_stations &&
      recommendation.nearest_fire_stations.length > 0
    ) {
      return recommendation.nearest_fire_stations.slice(0, 2);
    }
    return (recommendation?.responders || [])
      .filter(
        (r) =>
          r.type === "CHEMICAL_FIRE_STATION" ||
          r.type === "FIRE_STATION" ||
          r.type === "INDUSTRIAL_FIRE_SAFETY" ||
          r.type === "MUNICIPAL_FIRE_STATION"
      )
      .slice(0, 2);
  }, [recommendation]);

  const specializedResponders = useMemo(() => {
    if (
      recommendation?.specialized_responders &&
      recommendation.specialized_responders.length > 0
    ) {
      return recommendation.specialized_responders;
    }
    return (recommendation?.responders || []).filter(
      (r) =>
        r.type === "SPECIALIZED_HAZMAT_UNIT" ||
        r.type === "PORT_EMERGENCY_SERVICES"
    );
  }, [recommendation]);

  const ndrfResponder = useMemo(() => {
    if (
      recommendation?.ndrf_responders &&
      recommendation.ndrf_responders.length > 0
    ) {
      return recommendation.ndrf_responders[0];
    }
    return (recommendation?.responders || []).find(
      (r) => r.type === "NDRF" || r.type === "NDRF_DISASTER_BATTALION"
    );
  }, [recommendation]);

  const escalationState =
    recommendation?.escalation_decision?.escalation_state ||
    (recommendation?.auto_escalation_eligible
      ? "AUTOMATIC_ESCALATION"
      : recommendation?.response_priority === "REVIEW_REQUIRED"
      ? "ADMIN_REVIEW_REQUIRED"
      : "NO_ESCALATION");

  const isMedicalEscalation =
    Boolean(recommendation?.medical_escalation) ||
    Boolean(recommendation?.escalation_decision?.medical_escalation);

  return (
    <div
      id="emergency-response-section"
      className={cn(
        "rounded-control bg-surface/90 border border-border/80 font-mono text-xs overflow-hidden transition-all duration-200",
        className
      )}
    >
      {/* 1. Header with Response Priority */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-2.5 flex items-center justify-between cursor-pointer hover:bg-surface-hover/80 transition-colors border-b border-border/50"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              "w-6 h-6 rounded-control flex items-center justify-center shrink-0 border",
              escalationState === "AUTOMATIC_ESCALATION"
                ? "bg-state-error/15 border-state-error/30 text-state-error"
                : escalationState === "ADMIN_REVIEW_REQUIRED"
                ? "bg-accent/15 border-accent/30 text-accent"
                : "bg-surface-hover border-border text-foreground-muted"
            )}
          >
            <Siren className="w-3.5 h-3.5 animate-pulse-subtle" />
          </div>
          <div className="min-w-0">
            <span className="text-[10.5px] text-foreground font-bold uppercase tracking-wider block truncate">
              EMERGENCY RESPONSE & REGULATION
            </span>
            <span className="text-[9px] text-foreground-muted block">
              Authoritative escalation & geospatial dispatch
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {recommendation && (
            <span
              className={cn(
                "text-[9.5px] px-2 py-0.5 rounded border font-bold",
                priorityStyles.bg,
                priorityStyles.text,
                priorityStyles.border
              )}
            >
              {recommendation.response_priority}
            </span>
          )}
          <button
            type="button"
            title={isExpanded ? "Collapse emergency response" : "Expand emergency response"}
            className="p-0.5 text-foreground-muted hover:text-foreground"
          >
            {isExpanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* 2. Expanded Content */}
      {isExpanded && (
        <div className="p-3 space-y-3 animate-in fade-in duration-150">
          {/* Success Banner if notification just triggered */}
          {feedbackMessage && (
            <div
              className={cn(
                "p-2 rounded-control border text-[10px] font-mono flex items-center gap-2 animate-in slide-in-from-top-2 duration-150",
                feedbackMessage.includes("fail") || feedbackMessage.includes("could not")
                  ? "bg-state-warning/15 border-state-warning/30 text-state-warning"
                  : "bg-state-success/15 border-state-success/30 text-state-success"
              )}
            >
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">{feedbackMessage}</span>
            </div>
          )}

          {/* Demo Alert Number Configuration Input */}
          <div className="p-2.5 rounded-control bg-background/90 border border-border/80 space-y-1.5">
            <div className="flex items-center justify-between text-[10px]">
              <span className="font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Smartphone className="w-3 h-3 text-accent" />
                Demo Alert Destination Number
              </span>
              {phoneSavedFeedback && (
                <span className="text-[9px] text-state-success font-semibold animate-pulse">
                  ✓ Applied
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                placeholder="+91 9876543210"
                className="flex-1 px-2.5 py-1 rounded bg-surface border border-border text-foreground font-mono text-xs focus:outline-none focus:border-accent"
              />
              <button
                type="button"
                onClick={handleApplyPhone}
                className="px-2.5 py-1 rounded bg-accent text-white font-bold text-[10px] flex items-center gap-1 shadow-panel transition-all active:scale-95 hover:bg-accent/90 shrink-0"
              >
                <Save className="w-3 h-3" />
                <span>Save / Apply</span>
              </button>
            </div>
            <div className="text-[9px] text-foreground-muted">
              Demo notifications (SMS + WhatsApp) will be dispatched to this number.
            </div>
          </div>

          {/* Authoritative Escalation State Banners */}
          {escalationState === "AUTOMATIC_ESCALATION" && (
            <div className="p-2.5 rounded-control bg-state-error/15 border border-state-error/40 text-[10.5px] text-state-error flex items-start gap-2 animate-in zoom-in-95">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <div className="font-bold uppercase tracking-wider text-[11px]">
                  AUTOMATIC ESCALATION TRIGGERED
                </div>
                <div className="text-foreground-secondary text-[10px]">
                  Authoritative policy has triggered automated multi-channel demo escalation ({confidencePercent.toFixed(1)}% confidence).
                </div>
              </div>
            </div>
          )}

          {escalationState === "ADMIN_REVIEW_REQUIRED" && (
            <div className="p-2.5 rounded-control bg-accent/15 border border-accent/40 text-[10.5px] text-accent flex items-start gap-2">
              <Siren className="w-4 h-4 shrink-0 mt-0.5 animate-pulse-subtle" />
              <div className="space-y-0.5">
                <div className="font-bold uppercase tracking-wider text-[11px]">
                  ADMIN REVIEW REQUIRED
                </div>
                <div className="text-foreground-secondary text-[10px]">
                  High-confidence event detected ({confidencePercent.toFixed(1)}%). Operator review &amp; authorization required before dispatch.
                </div>
              </div>
            </div>
          )}

          {escalationState === "NO_ESCALATION" && (
            <div className="p-2.5 rounded-control bg-surface-hover/80 border border-border/70 text-[10.5px] text-foreground-secondary flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-foreground-muted" />
              <div className="space-y-0.5">
                <div className="font-bold uppercase tracking-wider text-[10.5px] text-foreground">
                  STANDBY MONITORING
                </div>
                <div className="text-foreground-muted text-[9.5px]">
                  Standard confidence profile ({confidencePercent.toFixed(1)}%). Automatic emergency escalation on standby.
                </div>
              </div>
            </div>
          )}

          {/* Medical Escalation Banner */}
          {isMedicalEscalation && (
            <div className="p-2.5 rounded-control bg-state-error/10 border border-state-error/30 text-[10.5px] text-state-error flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <div className="font-bold uppercase tracking-wider text-[11px]">
                  MEDICAL ESCALATION INDICATED
                </div>
                <div className="text-foreground-secondary text-[10px]">
                  Critical severity or industrial burn exposure risk. Burn ICU trauma admission and ambulance readiness recommended.
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading ? (
            <div className="py-5 flex flex-col items-center justify-center text-foreground-muted gap-2">
              <div className="w-5 h-5 rounded-full border-2 border-accent/20 border-t-accent animate-spin" />
              <span className="text-[10px]">Evaluating geodesic proximity &amp; escalation policy...</span>
            </div>
          ) : isError ? (
            /* Error State with Retry Button */
            <div className="p-3 rounded-control bg-state-error/10 border border-state-error/30 text-center space-y-2">
              <div className="text-state-error flex items-center justify-center gap-1.5 text-xs font-semibold">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage || "Unable to load emergency response intelligence."}</span>
              </div>
              <button
                type="button"
                onClick={() => loadData()}
                className="px-3 py-1 bg-surface border border-border text-foreground hover:bg-surface-hover rounded text-[10px] font-bold inline-flex items-center gap-1.5 transition-colors"
              >
                <RotateCw className="w-3 h-3" />
                <span>Retry Connection</span>
              </button>
            </div>
          ) : !recommendation || recommendation.responders.length === 0 ? (
            /* Genuinely Empty State */
            <div className="text-center py-4 text-foreground-muted text-[11px] space-y-1">
              <HelpCircle className="w-4 h-4 mx-auto text-foreground-muted/60" />
              <div>No applicable emergency responders found within operational radius.</div>
            </div>
          ) : (
            <>
              {/* Operational Priority & Policy Drivers */}
              <div className="p-2 rounded-control bg-background/80 border border-border/60 space-y-1.5">
                <div className="text-[10px] text-foreground-secondary leading-relaxed">
                  <span className="font-semibold text-foreground">Operational Rationale: </span>
                  <span>{recommendation.priority_reason}</span>
                </div>

                {recommendation.policy_drivers && recommendation.policy_drivers.length > 0 && (
                  <div className="pt-1 border-t border-border/40 space-y-1 text-[9.5px]">
                    <span className="text-foreground-muted uppercase tracking-wider font-semibold block text-[8.5px]">
                      Active Policy Drivers
                    </span>
                    {recommendation.policy_drivers.map((driver, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-foreground-secondary">
                        <CheckCircle2 className="w-3 h-3 text-accent shrink-0" />
                        <span>{driver.replace(/_/g, " ")}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 3. Nearest Hospitals & Burn ICUs */}
              {nearestHospitals.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-foreground-muted uppercase tracking-wider border-b border-border/40 pb-1 font-semibold">
                    <span className="flex items-center gap-1 text-accent-cyan">
                      🏥 Nearest Hospitals &amp; Burn ICUs ({nearestHospitals.length})
                    </span>
                    <span className="text-[8.5px] text-accent-cyan font-bold">GEODESIC MATCH</span>
                  </div>

                  <div className="space-y-2">
                    {nearestHospitals.map((resp) => (
                      <div
                        key={resp.id}
                        className="p-2.5 rounded-control bg-surface border border-accent-cyan/20 flex flex-col gap-1.5 transition-all hover:border-accent-cyan/50"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm shrink-0">🏥</span>
                              <span className="font-semibold text-foreground text-[11px] truncate">
                                {resp.name}
                              </span>
                            </div>
                            <div className="text-[9.5px] text-foreground-muted truncate pl-5">
                              {resp.city}, {resp.state}
                            </div>
                          </div>

                          <span className="text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase border bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20 shrink-0">
                            {resp.type.replace(/_/g, " ")}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-1 text-[10px] text-foreground-secondary bg-background/50 p-1.5 rounded border border-border/40 font-mono">
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">DIST</span>
                            <span className="font-semibold text-foreground">{resp.formatted_distance}</span>
                          </div>
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">EST. ETA</span>
                            <span className="font-semibold text-accent-cyan">{resp.formatted_eta}</span>
                          </div>
                          <div className="truncate">
                            <span className="text-foreground-muted block text-[8.5px]">CONTACT</span>
                            <span className="font-semibold text-foreground truncate">{resp.phone || "N/A"}</span>
                          </div>
                        </div>

                        <div className="text-[9.5px] text-foreground-secondary/90 flex items-start gap-1 leading-tight">
                          <Info className="w-2.5 h-2.5 text-accent-cyan shrink-0 mt-0.5" />
                          <span>{resp.recommendation_reason}</span>
                        </div>

                        {resp.capabilities && resp.capabilities.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-0.5">
                            {resp.capabilities.map((cap, cIdx) => (
                              <span
                                key={cIdx}
                                className="px-1.5 py-0.2 rounded bg-surface-hover text-[8.5px] text-foreground-muted border border-border/50"
                              >
                                {cap}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="pt-1.5 border-t border-border/40 flex items-center justify-between">
                          <span className="text-[8px] text-foreground-muted truncate max-w-[150px]">
                            Src: {resp.source}
                          </span>

                          <button
                            type="button"
                            onClick={() => handleOpenConfirm(resp, "NOTIFY")}
                            className="px-2.5 py-1 rounded-control text-[10px] font-bold flex items-center gap-1 shadow-panel transition-all active:scale-95 bg-accent-cyan/20 border border-accent-cyan/40 text-accent-cyan hover:bg-accent-cyan/30"
                          >
                            <Send className="w-3 h-3" />
                            <span>NOTIFY HOSPITAL</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. Nearest Fire Stations */}
              {nearestFireStations.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-foreground-muted uppercase tracking-wider border-b border-border/40 pb-1 font-semibold">
                    <span className="flex items-center gap-1 text-accent">
                      🚒 Nearest Fire Stations ({nearestFireStations.length})
                    </span>
                    <span className="text-[8.5px] text-accent font-bold">GEODESIC MATCH</span>
                  </div>

                  <div className="space-y-2">
                    {nearestFireStations.map((resp) => (
                      <div
                        key={resp.id}
                        className="p-2.5 rounded-control bg-surface border border-accent/20 flex flex-col gap-1.5 transition-all hover:border-accent/50"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm shrink-0">🚒</span>
                              <span className="font-semibold text-foreground text-[11px] truncate">
                                {resp.name}
                              </span>
                            </div>
                            <div className="text-[9.5px] text-foreground-muted truncate pl-5">
                              {resp.city}, {resp.state}
                            </div>
                          </div>

                          <span className="text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase border bg-accent/10 text-accent border-accent/20 shrink-0">
                            {resp.type.replace(/_/g, " ")}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-1 text-[10px] text-foreground-secondary bg-background/50 p-1.5 rounded border border-border/40 font-mono">
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">DIST</span>
                            <span className="font-semibold text-foreground">{resp.formatted_distance}</span>
                          </div>
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">EST. ETA</span>
                            <span className="font-semibold text-accent">{resp.formatted_eta}</span>
                          </div>
                          <div className="truncate">
                            <span className="text-foreground-muted block text-[8.5px]">CONTACT</span>
                            <span className="font-semibold text-foreground truncate">{resp.phone || "N/A"}</span>
                          </div>
                        </div>

                        <div className="text-[9.5px] text-foreground-secondary/90 flex items-start gap-1 leading-tight">
                          <Info className="w-2.5 h-2.5 text-accent shrink-0 mt-0.5" />
                          <span>{resp.recommendation_reason}</span>
                        </div>

                        {resp.capabilities && resp.capabilities.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-0.5">
                            {resp.capabilities.map((cap, cIdx) => (
                              <span
                                key={cIdx}
                                className="px-1.5 py-0.2 rounded bg-surface-hover text-[8.5px] text-foreground-muted border border-border/50"
                              >
                                {cap}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="pt-1.5 border-t border-border/40 flex items-center justify-between">
                          <span className="text-[8px] text-foreground-muted truncate max-w-[150px]">
                            Src: {resp.source}
                          </span>

                          <button
                            type="button"
                            onClick={() => handleOpenConfirm(resp, "NOTIFY")}
                            className="px-2.5 py-1 rounded-control text-[10px] font-bold flex items-center gap-1 shadow-panel transition-all active:scale-95 bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30"
                          >
                            <Send className="w-3 h-3" />
                            <span>NOTIFY FIRE COMMAND</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 5. Specialized Responders (HAZMAT / Port Emergency) */}
              {specializedResponders.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-foreground-muted uppercase tracking-wider border-b border-border/40 pb-1 font-semibold">
                    <span className="flex items-center gap-1 text-accent">
                      ☣ Specialized HAZMAT &amp; Port Emergency ({specializedResponders.length})
                    </span>
                    <span className="text-[8.5px] text-accent font-bold">SPECIALIZED</span>
                  </div>

                  <div className="space-y-2">
                    {specializedResponders.map((resp) => (
                      <div
                        key={resp.id}
                        className="p-2.5 rounded-control bg-surface border border-accent/20 flex flex-col gap-1.5 transition-all hover:border-accent/50"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm shrink-0">☣</span>
                              <span className="font-semibold text-foreground text-[11px] truncate">
                                {resp.name}
                              </span>
                            </div>
                            <div className="text-[9.5px] text-foreground-muted truncate pl-5">
                              {resp.city}, {resp.state}
                            </div>
                          </div>

                          <span className="text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase border bg-accent/10 text-accent border-accent/20 shrink-0">
                            {resp.type.replace(/_/g, " ")}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-1 text-[10px] text-foreground-secondary bg-background/50 p-1.5 rounded border border-border/40 font-mono">
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">DIST</span>
                            <span className="font-semibold text-foreground">{resp.formatted_distance}</span>
                          </div>
                          <div>
                            <span className="text-foreground-muted block text-[8.5px]">EST. ETA</span>
                            <span className="font-semibold text-accent">{resp.formatted_eta}</span>
                          </div>
                          <div className="truncate">
                            <span className="text-foreground-muted block text-[8.5px]">CONTACT</span>
                            <span className="font-semibold text-foreground truncate">{resp.phone || "N/A"}</span>
                          </div>
                        </div>

                        <div className="text-[9.5px] text-foreground-secondary/90 flex items-start gap-1 leading-tight">
                          <Info className="w-2.5 h-2.5 text-accent shrink-0 mt-0.5" />
                          <span>{resp.recommendation_reason}</span>
                        </div>

                        <div className="pt-1.5 border-t border-border/40 flex items-center justify-between">
                          <span className="text-[8px] text-foreground-muted truncate max-w-[150px]">
                            Src: {resp.source}
                          </span>

                          <button
                            type="button"
                            onClick={() => handleOpenConfirm(resp, "NOTIFY")}
                            className="px-2.5 py-1 rounded-control text-[10px] font-bold flex items-center gap-1 shadow-panel transition-all active:scale-95 bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30"
                          >
                            <Send className="w-3 h-3" />
                            <span>NOTIFY HAZMAT UNIT</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 6. NDRF Regional Battalion if present */}
              {ndrfResponder && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] text-foreground-muted uppercase tracking-wider border-b border-border/40 pb-1 font-semibold">
                    <span className="flex items-center gap-1 text-state-error">
                      🛡 Regional Disaster Battalion (NDRF)
                    </span>
                    <span className="text-[8.5px] text-state-error font-bold">CBRN / HAZMAT</span>
                  </div>

                  <div className="p-2.5 rounded-control bg-surface border border-state-error/30 flex flex-col gap-1.5 transition-all hover:border-state-error/60">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm shrink-0">🛡</span>
                          <span className="font-semibold text-foreground text-[11px] truncate">
                            {ndrfResponder.name}
                          </span>
                        </div>
                        <div className="text-[9.5px] text-foreground-muted truncate pl-5">
                          {ndrfResponder.city}, {ndrfResponder.state}
                        </div>
                      </div>

                      <span className="text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase border bg-state-error/10 text-state-error border-state-error/20 shrink-0">
                        NDRF
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-1 text-[10px] text-foreground-secondary bg-background/50 p-1.5 rounded border border-border/40 font-mono">
                      <div>
                        <span className="text-foreground-muted block text-[8.5px]">DIST</span>
                        <span className="font-semibold text-foreground">{ndrfResponder.formatted_distance}</span>
                      </div>
                      <div>
                        <span className="text-foreground-muted block text-[8.5px]">EST. ETA</span>
                        <span className="font-semibold text-state-error">{ndrfResponder.formatted_eta}</span>
                      </div>
                      <div className="truncate">
                        <span className="text-foreground-muted block text-[8.5px]">CONTACT</span>
                        <span className="font-semibold text-foreground truncate">{ndrfResponder.phone || "N/A"}</span>
                      </div>
                    </div>

                    <div className="pt-1.5 border-t border-border/40 flex items-center justify-between">
                      <span className="text-[8px] text-foreground-muted truncate max-w-[150px]">
                        Src: {ndrfResponder.source}
                      </span>

                      <button
                        type="button"
                        onClick={() => handleOpenConfirm(ndrfResponder, "MOBILIZE")}
                        className="px-2.5 py-1 rounded-control text-[10px] font-bold flex items-center gap-1 shadow-panel transition-all active:scale-95 bg-state-error/20 border border-state-error/40 text-state-error hover:bg-state-error/30"
                      >
                        <Send className="w-3 h-3" />
                        <span>MOBILIZE NDRF</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 7. Session Activity Audit Log */}
              <div className="pt-2 border-t border-border/50">
                <ResponseActivityFeed records={activity} />
              </div>
            </>
          )}
        </div>
      )}

      {/* Confirmation Dialog Modal */}
      <NotificationConfirmModal
        isOpen={confirmModalState.isOpen}
        responder={confirmModalState.responder}
        eventId={event.event_id}
        priority={recommendation?.response_priority || "MEDIUM"}
        action={confirmModalState.action}
        demoPhone={demoPhone}
        onConfirm={handleConfirmNotification}
        onClose={() =>
          setConfirmModalState({
            isOpen: false,
            responder: null,
            action: "NOTIFY",
          })
        }
      />
    </div>
  );
}
