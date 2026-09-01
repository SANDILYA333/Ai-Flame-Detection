"use client";

import React from "react";
import { AlertTriangle, RotateCw, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EventDetailErrorProps {
  message?: string;
  onRetry?: () => void;
  onClose?: () => void;
  className?: string;
}

export function EventDetailError({
  message = "Unable to retrieve event intelligence from backend pipeline.",
  onRetry,
  onClose,
  className,
}: EventDetailErrorProps) {
  return (
    <div
      className={cn(
        "w-full sm:w-96 p-4 rounded-panel bg-surface-raised/95 backdrop-blur-md border border-border space-y-3 font-mono text-xs select-none shadow-panel text-center",
        className
      )}
    >
      <div className="flex justify-end">
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-control text-foreground-muted hover:text-foreground hover:bg-surface-hover transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="w-10 h-10 rounded-full bg-state-error/15 border border-state-error/30 text-state-error mx-auto flex items-center justify-center">
        <AlertTriangle className="w-5 h-5" />
      </div>

      <div>
        <div className="font-bold text-foreground">INTELLIGENCE UNAVAILABLE</div>
        <p className="text-[11px] text-foreground-muted mt-1 max-w-[240px] mx-auto">
          {message}
        </p>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-accent/15 border border-accent/30 text-accent hover:bg-accent/25 transition-colors font-semibold text-[11px]"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Retry Request</span>
        </button>
      )}
    </div>
  );
}
