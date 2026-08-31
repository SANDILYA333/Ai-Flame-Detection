import React from "react";
import { cn } from "@/lib/utils";

export interface LoadingIndicatorProps {
  label?: string;
  size?: "sm" | "md" | "lg";
  variant?: "spinner" | "skeleton" | "radar";
  className?: string;
}

export function LoadingIndicator({
  label = "Processing telemetry...",
  size = "md",
  variant = "spinner",
  className,
}: LoadingIndicatorProps) {
  if (variant === "skeleton") {
    return (
      <div className={cn("space-y-2 w-full animate-pulse", className)}>
        <div className="h-4 bg-surface-raised rounded w-3/4" />
        <div className="h-3 bg-surface-raised rounded w-1/2" />
        <div className="h-3 bg-surface-raised rounded w-5/6" />
      </div>
    );
  }

  const spinnerSizes = {
    sm: "w-3.5 h-3.5 border-2",
    md: "w-5 h-5 border-2",
    lg: "w-8 h-8 border-3",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 text-foreground-muted p-4", className)}>
      <div
        className={cn(
          "rounded-full border-accent/20 border-t-accent animate-spin",
          spinnerSizes[size]
        )}
      />
      {label && <span className="text-[11px] font-mono tracking-wider uppercase">{label}</span>}
    </div>
  );
}
