import React from "react";
import { cn } from "@/lib/utils";

export interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "standard" | "elevated" | "glass";
  compact?: boolean;
}

export function Panel({
  className,
  variant = "standard",
  compact = false,
  children,
  ...props
}: PanelProps) {
  const baseStyles =
    "rounded-panel border transition-all duration-200 overflow-hidden shadow-panel";

  const variantStyles = {
    standard: "bg-surface border-border",
    elevated: "bg-surface-raised border-border-strong",
    glass: "bg-surface/90 backdrop-blur-md border-border",
  };

  const paddingStyles = compact ? "p-2.5" : "p-4";

  return (
    <div className={cn(baseStyles, variantStyles[variant], paddingStyles, className)} {...props}>
      {children}
    </div>
  );
}
