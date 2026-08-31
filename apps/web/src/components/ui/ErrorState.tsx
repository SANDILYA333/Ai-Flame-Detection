import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "SERVICE UNAVAILABLE",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-6 bg-state-error/5 border border-state-error/30 rounded-panel",
        className
      )}
    >
      <div className="w-8 h-8 rounded-full bg-state-error/15 flex items-center justify-center text-state-error mb-2.5">
        <AlertTriangle className="w-4 h-4" />
      </div>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-state-error font-sans">
        {title}
      </h4>
      <p className="text-[11px] text-foreground-muted mt-1 max-w-[280px] font-mono leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-3 h-3" />}
          className="mt-3.5 border-state-error/40 text-state-error hover:bg-state-error/10"
        >
          Retry Connection
        </Button>
      )}
    </div>
  );
}
