import React from "react";
import { cn } from "@/lib/utils";

export interface StatusDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: "live" | "warning" | "error" | "offline" | "thermal";
  pulse?: boolean;
  size?: "sm" | "md" | "lg";
}

export function StatusDot({
  className,
  status = "live",
  pulse = false,
  size = "md",
  ...props
}: StatusDotProps) {
  const statusColors = {
    live: "bg-accent",
    warning: "bg-state-warning",
    error: "bg-state-error",
    offline: "bg-foreground-disabled",
    thermal: "bg-thermal",
  };

  const sizeStyles = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };

  return (
    <span className={cn("relative inline-flex items-center justify-center", className)} {...props}>
      {pulse && (
        <span
          className={cn(
            "absolute rounded-full opacity-75 animate-ping",
            statusColors[status],
            sizeStyles[size]
          )}
        />
      )}
      <span className={cn("relative rounded-full", statusColors[status], sizeStyles[size])} />
    </span>
  );
}
