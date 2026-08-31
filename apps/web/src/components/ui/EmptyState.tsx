import React from "react";
import { CircleSlash } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon = <CircleSlash className="w-8 h-8 text-foreground-disabled" />,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-6 bg-surface-raised/40 border border-border/60 rounded-panel",
        className
      )}
    >
      <div className="mb-2.5">{icon}</div>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground font-sans">
        {title}
      </h4>
      {description && (
        <p className="text-[11px] text-foreground-muted mt-1 max-w-[240px] font-mono leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
