import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "success" | "warning" | "error" | "info" | "thermal" | "industrial" | "review";
  size?: "sm" | "md";
  dot?: boolean;
}

export function Badge({
  className,
  variant = "neutral",
  size = "md",
  dot = false,
  children,
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center font-mono font-medium rounded-pill tracking-wider uppercase select-none border";

  const variantStyles = {
    neutral: "bg-surface-raised border-border text-foreground-secondary",
    success: "bg-accent/10 border-accent/30 text-accent",
    warning: "bg-state-warning/10 border-state-warning/30 text-state-warning",
    error: "bg-state-error/10 border-state-error/30 text-state-error",
    info: "bg-state-info/10 border-state-info/30 text-state-info",
    thermal: "bg-thermal/10 border-thermal/30 text-thermal",
    industrial: "bg-accent/15 border-accent/40 text-accent",
    review: "bg-state-warning/15 border-state-warning/40 text-state-warning",
  };

  const sizeStyles = {
    sm: "text-[10px] px-1.5 py-0.5 gap-1",
    md: "text-[11px] px-2 py-0.5 gap-1.5",
  };

  const dotColors = {
    neutral: "bg-foreground-muted",
    success: "bg-accent",
    warning: "bg-state-warning",
    error: "bg-state-error",
    info: "bg-state-info",
    thermal: "bg-thermal",
    industrial: "bg-accent",
    review: "bg-state-warning",
  };

  return (
    <span className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)} {...props}>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", dotColors[variant])} />}
      {children}
    </span>
  );
}
