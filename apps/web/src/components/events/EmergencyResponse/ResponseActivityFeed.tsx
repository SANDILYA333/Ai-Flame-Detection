"use client";

import React from "react";
import type { ResponseActivityRecord } from "@/types/responders";
import { History, CheckCircle2, Clock, Send, ShieldAlert } from "lucide-react";
import { formatRelativeSecondsAgo, formatUtcTime } from "@/lib/format/dates";
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

  return (
    <div className={cn("space-y-1.5 font-mono text-[10.5px]", className)}>
      <div className="flex items-center justify-between text-foreground-muted pb-1 border-b border-border/40">
        <span className="uppercase tracking-wider flex items-center gap-1 font-semibold text-[9.5px]">
          <History className="w-3 h-3 text-accent-cyan" />
          Session Response Activity ({records.length})
        </span>
        <span className="text-[9px] text-accent font-bold px-1.5 py-0.2 rounded bg-accent/10 border border-accent/20">
          SIMULATED AUDIT
        </span>
      </div>

      <div className="space-y-1.5 max-h-36 overflow-y-auto scrollbar-thin pr-0.5">
        {records.map((rec) => {
          const isMobilize = rec.action === "MOBILIZE";
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
                      isMobilize ? "bg-state-error/20 text-state-error" : "bg-state-success/20 text-state-success"
                    )}
                  >
                    <CheckCircle2 className="w-2.5 h-2.5" />
                  </div>
                  <span className="font-semibold text-foreground truncate max-w-[170px]">
                    {rec.responder_name}
                  </span>
                </div>
                <span className="text-[9px] px-1 py-0.2 rounded font-bold bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 shrink-0">
                  {rec.status}
                </span>
              </div>

              <div className="flex items-center justify-between text-[9.5px] text-foreground-muted">
                <span className="text-foreground-secondary font-medium">
                  {isMobilize ? "NDRF Mobilization Request" : "Emergency Response Alert"}
                </span>
                <span className="text-foreground-muted flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" />
                  {isNaN(date.getTime()) ? "Just now" : formatUtcTime(date)}
                </span>
              </div>

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
