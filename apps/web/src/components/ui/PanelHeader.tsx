import React from "react";
import { cn } from "@/lib/utils";

export interface PanelHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  onClose?: () => void;
}

export function PanelHeader({
  className,
  title,
  subtitle,
  icon,
  actions,
  onClose,
  children,
  ...props
}: PanelHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between pb-2.5 mb-2.5 border-b border-border/80",
        className
      )}
      {...props}
    >
      <div className="flex items-center gap-2 min-w-0">
        {icon && <span className="text-foreground-secondary shrink-0">{icon}</span>}
        <div className="min-w-0">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground truncate font-sans">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[10px] text-foreground-muted truncate font-mono mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        {actions}
        {children}
        {onClose && (
          <button
            onClick={onClose}
            aria-label="Close panel"
            className="w-5 h-5 rounded flex items-center justify-center text-foreground-muted hover:text-foreground hover:bg-surface-hover transition-colors"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
