"use client";

import React from "react";
import { AgniStatus as StatusType } from "@/services/agni/agniTypes";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/ui/StatusDot";

export interface AgniStatusProps {
  status: StatusType;
  className?: string;
  showDot?: boolean;
}

export function AgniStatus({
  status,
  className,
  showDot = true,
}: AgniStatusProps) {
  const config = React.useMemo(() => {
    switch (status) {
      case "activating":
        return {
          label: "ACTIVATING...",
          dotVariant: "warning" as const,
          containerClass: "bg-state-warning/10 border-state-warning/30 text-state-warning",
          pulse: true,
        };
      case "listening":
        return {
          label: "LISTENING",
          dotVariant: "live" as const,
          containerClass: "bg-accent/15 border-accent/40 text-accent font-bold",
          pulse: true,
        };
      case "processing":
        return {
          label: "INTERPRETING",
          dotVariant: "live" as const,
          containerClass: "bg-accent-cyan/15 border-accent-cyan/40 text-accent-cyan font-semibold",
          pulse: true,
        };
      case "speaking":
        return {
          label: "RESPONDING",
          dotVariant: "live" as const,
          containerClass: "bg-accent/15 border-accent/40 text-accent font-bold",
          pulse: false,
        };
      case "error":
        return {
          label: "ERROR / BLOCKED",
          dotVariant: "error" as const,
          containerClass: "bg-state-error/15 border-state-error/40 text-state-error font-bold",
          pulse: false,
        };
      case "idle":
      default:
        return {
          label: "READY",
          dotVariant: "offline" as const,
          containerClass: "bg-surface-raised border-border text-foreground-secondary",
          pulse: false,
        };
    }
  }, [status]);

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill border text-[10px] font-mono tracking-wider select-none",
        config.containerClass,
        className
      )}
      aria-live="polite"
      aria-atomic="true"
    >
      {showDot && (
        <StatusDot
          status={config.dotVariant}
          pulse={config.pulse}
          size="sm"
        />
      )}
      <span>{config.label}</span>
    </div>
  );
}
