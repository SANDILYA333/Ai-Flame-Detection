"use client";

import React from "react";
import type { ResponseActivityRecord } from "@/types/responders";
import { History, CheckCircle2, Clock, Smartphone, MessageSquare, AlertTriangle, ShieldCheck } from "lucide-react";
import { formatUtcTime } from "@/lib/format/dates";
import { cn } from "@/lib/utils";

export interface ResponseActivityFeedProps {
  records: ResponseActivityRecord[];
  className?: string;
}

export function ResponseActivityFeed({ records, className }: ResponseActivityFeedProps) {
  if (!records || records.length === 0) {
    return (
      <div className={cn("p-2.5 rounded-control bg-surface/60 border border-border/60 text-center font-mono text-[10.5px] text-foreground-muted", className)}>
        <History className="w-3.5 h-3.5 mx-auto mb-1 opacity-60 text-foreground-muted" />
        <span>No notification actions recorded in this session.</span>
      </div>
    );
  }

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case "DELIVERED":
        return "bg-state-success/15 text-state-success border-state-success/30";
      case "SENT":
      case "PROVIDER_ACCEPTED":
        return "bg-accent/15 text-accent border-accent/30";
      case "SIMULATED":
        return "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/30";
      case "DUPLICATE_SUPPRESSED":
        return "bg-foreground-muted/15 text-foreground-muted border-border/60";
      case "FAILED":
      case "TIMEOUT":
      case "PROVIDER_REJECTED":
        return "bg-state-error/15 text-state-error border-state-error/30";
      default:
        return "bg-state-warning/15 text-state-warning border-state-warning/30";
    }
  };

  return (
    <div className={cn("space-y-1.5 font-mono text-[10.5px]", className)}>
      <div className="flex items-center justify-between text-foreground-muted pb-1 border-b border-border/40">
        <span className="uppercase tracking-wider flex items-center gap-1 font-semibold text-[9.5px]">
          <History className="w-3 h-3 text-accent-cyan" />
          Authoritative Response Audit Log ({records.length})
        </span>
        <span className="text-[9px] text-accent font-bold px-1.5 py-0.2 rounded bg-accent/10 border border-accent/20">
          AUDIT TRAIL
        </span>
      </div>

      <div className="space-y-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-0.5">
        {records.map((rec) => {
          const isMobilize = rec.action === "MOBILIZE";
          const isAuto = rec.escalation_type === "HIGH_CONFIDENCE_AUTO" || rec.escalation_type === "CRITICAL_MEDICAL";
          const isSuppressed = rec.status === "DUPLICATE_SUPPRESSED";
          const displayPhone = rec.destination_masked || rec.recipient_phone;
          const date = new Date(rec.timestamp);

          return (
            <div
              key={rec.notification_id}
              className="p-2 rounded-control bg-surface border border-border/70 flex flex-col gap-1 transition-colors hover:border-accent/40"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 min-w-0">
                  <div
                    className={cn(
                      "w-4 h-4 rounded-full flex items-center justify-center shrink-0",
                      isSuppressed
                        ? "bg-foreground-muted/20 text-foreground-muted"
                        : isMobilize
                        ? "bg-state-error/20 text-state-error"
                        : "bg-state-success/20 text-state-success"
                    )}
                  >
                    {isSuppressed ? (
                      <ShieldCheck className="w-2.5 h-2.5" />
                    ) : (
                      <CheckCircle2 className="w-2.5 h-2.5" />
                    )}
                  </div>
                  <span className="font-semibold text-foreground truncate max-w-[170px]">
                    {rec.responder_name}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {rec.escalation_type && (
                    <span
                      className={cn(
                        "text-[8px] px-1 py-0.2 rounded font-bold border",
                        isAuto
                          ? "bg-state-error/10 text-state-error border-state-error/20"
                          : "bg-surface-hover text-foreground-muted border-border/40"
                      )}
                    >
                      {rec.escalation_type.replace(/_/g, " ")}
                    </span>
                  )}
                  <span
                    className={cn(
                      "text-[9px] px-1.5 py-0.2 rounded font-bold border",
                      getStatusBadgeStyle(rec.status)
                    )}
                  >
                    {rec.status.replace(/_/g, " ")}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[9.5px] text-foreground-muted">
                <span className="text-foreground-secondary font-medium truncate max-w-[190px]">
                  {isMobilize ? "NDRF Mobilization" : "Emergency Response Alert"}
                  {displayPhone ? ` (${displayPhone})` : ""}
                </span>
                <span className="text-foreground-muted flex items-center gap-1 shrink-0">
                  <Clock className="w-2.5 h-2.5" />
                  {isNaN(date.getTime()) ? "Just now" : formatUtcTime(date)}
                </span>
              </div>

              {/* Multi-Channel Delivery Breakdown */}
              {rec.channels && rec.channels.length > 0 && (
                <div className="flex items-center gap-1.5 pt-0.5">
                  {rec.channels.map((ch, cIdx) => (
                    <span
                      key={cIdx}
                      className={cn(
                        "text-[8px] px-1.5 py-0.2 rounded flex items-center gap-1 font-semibold border",
                        getStatusBadgeStyle(ch.status)
                      )}
                    >
                      {ch.channel === "SMS" ? (
                        <Smartphone className="w-2 h-2" />
                      ) : (
                        <MessageSquare className="w-2 h-2" />
                      )}
                      {ch.channel}: {ch.status.replace(/_/g, " ")}
                      {ch.provider_message_id && !ch.provider_message_id.startsWith("SIM-") && (
                        <span className="opacity-75 text-[7.5px]">({ch.provider_message_id.slice(-6)})</span>
                      )}
                    </span>
                  ))}
                </div>
              )}

              {rec.analyst_notes && (
                <div className="text-[9px] text-foreground-muted/90 italic bg-background/60 p-1 rounded border border-border/40 truncate">
                  &quot;{rec.analyst_notes}&quot;
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
