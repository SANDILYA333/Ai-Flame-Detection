import React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, children, ...props }, ref) => {
    return (
      <div className="relative inline-flex w-full items-center">
        <select
          ref={ref}
          className={cn(
            "w-full h-8 pl-3 pr-8 text-xs bg-surface border rounded-control text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent disabled:opacity-40",
            error ? "border-state-error" : "border-border",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="absolute right-2.5 w-3.5 h-3.5 text-foreground-muted pointer-events-none" />
      </div>
    );
  }
);

Select.displayName = "Select";
