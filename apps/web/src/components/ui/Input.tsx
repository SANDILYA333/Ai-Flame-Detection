import React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full h-8 px-3 text-xs bg-surface border rounded-control text-foreground placeholder:text-foreground-disabled transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent disabled:opacity-40",
          error ? "border-state-error focus:ring-state-error" : "border-border",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
