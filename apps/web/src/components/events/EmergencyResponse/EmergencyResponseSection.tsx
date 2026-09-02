"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import type { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import type {
  EmergencyResponder,
  EventResponseRecommendation,
  ResponseActivityRecord,
  NotificationAction,
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
  MapPin,
  Building2,
  Phone,
  Send,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
  Sparkles,
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

  // Success toast feedback state
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // Load recommendations & activity whenever event changes
  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);

    async function loadData() {
      try {
        const [rec, act] = await Promise.all([
          fetchEventResponders(event),
          fetchResponseActivity(event.event_id),
        ]);
        if (!isCancelled) {
          setRecommendation(rec);
          setActivity(act);
          setIsLoading(false);
        }
      } catch {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isCancelled = true;
    };
  }, [event]);

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

  const handleConfirmNotification = async (notes?: string) => {
    if (!confirmModalState.responder) return;
    const resp = confirmModalState.responder;
    const action = confirmModalState.action;

    try {
      const result = await postNotifyResponder(
        event.event_id,
        {
          responder_id: resp.id,
          action,
          mode: "SIMULATED",
          analyst_notes: notes,
        },
        resp.name,
        resp.type
      );

      // Refresh activity list
      const updatedActivity = await fetchResponseActivity(event.event_id);
      setActivity(updatedActivity);

      // Show temporary feedback toast banner
      setFeedbackMessage(
        result.message || `✓ Notification simulated for ${resp.name}`
      );
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch (err) {
      console.error("Failed to submit notification:", err);
    }
  };

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

  return (
    <div
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
          <div className="w-6 h-6 rounded-control bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shrink-0">
            <Siren className="w-3.5 h-3.5 animate-pulse-subtle" />
          </div>
          <div className="min-w-0">
            <span className="text-[10px] text-foreground font-bold uppercase tracking-wider block truncate">
              Emergency Response & Notification
            </span>
            <span className="text-[9px] text-foreground-muted block">
              Analyst-confirmed emergency mobilization
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
          {/* Success Banner if notification just simulated */}
          {feedbackMessage && (
            <div className="p-2 rounded-control bg-state-success/15 border border-state-success/30 text-[10px] font-mono text-state-success flex items-center gap-2 animate-in slide-in-from-top-2 duration-150">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">{feedbackMessage}</span>
            </div>
          )}

          {isLoading ? (
            <div className="py-4 flex flex-col items-center justify-center text-foreground-muted gap-2">
              <div className="w-5 h-5 rounded-full border-2 border-accent/20 border-t-accent animate-spin" />
              <span className="text-[10px]">Calculating proximity & response policy...</span>
            </div>
          ) : !recommendation ? (
            <div className="text-center py-3 text-foreground-muted text-[11px]">
              No responder recommendations available.
            </div>
          ) : (
            <>
              {/* Operational Priority & Policy Disclaimer */}
              <div className="p-2 rounded-control bg-background/80 border border-border/60 space-y-1.5">
                <div className="text-[10px] text-foreground-secondary leading-relaxed">
                  <span className="font-semibold text-foreground">Operational Rationale: </span>
                  <span>{recommendation.priority_reason}</span>
                </div>

                {/* Recommendation Basis Checklist */}
                {recommendation.recommendation_basis.length > 0 && (
                  <div className="pt-1 border-t border-border/40 space-y-1 text-[9.5px]">
                    <span className="text-foreground-muted uppercase tracking-wider font-semibold block text-[8.5px]">
                      Recommendation Drivers
                    </span>
                    {recommendation.recommendation_basis.map((basis, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-foreground-secondary">
                        <CheckCircle2 className="w-3 h-3 text-accent shrink-0" />
                        <span>{basis}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Notice for Routine Flares or Review Required Events */}
              {recommendation.is_routine_flare && (
                <div className="p-2 rounded-control bg-state-success/10 border border-state-success/30 text-[10px] text-state-success flex items-start gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>
                    Routine operational flaring identified. Emergency dispatch is NOT indicated to prevent false alarms.
                  </span>
                </div>
              )}

              {recommendation.is_abstained_or_unknown && (
                <div className="p-2 rounded-control bg-state-warning/10 border border-state-warning/30 text-[10px] text-state-warning flex items-start gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>
                    Model uncertainty / low confidence. Mandatory analyst review before initiating external communication.
                  </span>
                </div>
              )}

              {/* 3. Recommended Responders List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[10px] text-foreground-muted uppercase tracking-wider border-b border-border/40 pb-1 font-semibold">
                  <span>Recommended Responders ({recommendation.responders.length})</span>
                  <span className="text-[8.5px] text-accent font-bold">WGS-84 PROXIMITY</span>
                </div>

                <div className="space-y-2">
                  {recommendation.responders.map((resp) => {
                    const isFire =
                      resp.type === "CHEMICAL_FIRE_STATION" ||
                      resp.type === "FIRE_STATION";
                    const isMed =
                      resp.type === "BURN_ICU" || resp.type === "HOSPITAL";
                    const isNdrf = resp.type === "NDRF";

                    return (
                      <div
                        key={resp.id}
                        className="p-2.5 rounded-control bg-surface border border-border/70 flex flex-col gap-1.5 transition-all hover:border-accent/50"
                      >
                        {/* Responder Header */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm shrink-0">
                                {isFire ? "🚒" : isMed ? "🏥" : "🛡"}
                              </span>
                              <span className="font-semibold text-foreground text-[11px] truncate">
                                {resp.name}
                              </span>
                            </div>
                            <div className="text-[9.5px] text-foreground-muted truncate pl-5">
                              {resp.city}, {resp.state}
                            </div>
                          </div>

                          <span
                            className={cn(
                              "text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase border shrink-0",
                              isFire
                                ? "bg-accent/10 text-accent border-accent/20"
                                : isMed
                                ? "bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20"
                                : "bg-state-error/10 text-state-error border-state-error/20"
                            )}
                          >
                            {resp.type.replace(/_/g, " ")}
                          </span>
                        </div>

                        {/* Distance, ETA and Phone */}
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
                            <span className="text-foreground-muted block text-[8.5px]">PHONE</span>
                            <span className="font-semibold text-foreground truncate">{resp.phone}</span>
                          </div>
                        </div>

                        {/* Recommendation Reason */}
                        <div className="text-[9.5px] text-foreground-secondary/90 flex items-start gap-1 leading-tight">
                          <Info className="w-2.5 h-2.5 text-accent shrink-0 mt-0.5" />
                          <span>{resp.recommendation_reason}</span>
                        </div>

                        {/* Capabilities Pills */}
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

                        {/* Action Buttons */}
                        <div className="pt-1.5 border-t border-border/40 flex items-center justify-between">
                          <span className="text-[8px] text-foreground-muted truncate max-w-[150px]">
                            Src: {resp.source}
                          </span>

                          <button
                            type="button"
                            onClick={() =>
                              handleOpenConfirm(
                                resp,
                                isNdrf ? "MOBILIZE" : "NOTIFY"
                              )
                            }
                            className={cn(
                              "px-2.5 py-1 rounded-control text-[10px] font-bold flex items-center gap-1 shadow-panel transition-all active:scale-95",
                              isNdrf
                                ? "bg-state-error/20 border border-state-error/40 text-state-error hover:bg-state-error/30"
                                : "bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30"
                            )}
                          >
                            <Send className="w-3 h-3" />
                            <span>{isNdrf ? "MOBILIZE NDRF" : "NOTIFY"}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 4. Session Activity Audit Log */}
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
