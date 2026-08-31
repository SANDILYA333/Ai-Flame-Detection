import React from "react";
import { cn } from "@/lib/utils";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "active" | "ghost" | "thermal";
  size?: "sm" | "md" | "lg";
  ariaLabel: string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, variant = "default", size = "md", ariaLabel, children, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center transition-all duration-150 rounded-control focus:outline-none focus:ring-1 focus:ring-accent border active:scale-95 cursor-pointer select-none disabled:opacity-40 disabled:pointer-events-none";

    const variantStyles = {
      default:
        "bg-surface border-border text-foreground-secondary hover:text-foreground hover:bg-surface-hover hover:border-border-strong",
      active:
        "bg-accent/15 border-accent text-accent shadow-inset",
      ghost:
        "bg-transparent border-transparent text-foreground-secondary hover:text-foreground hover:bg-surface-hover",
      thermal:
        "bg-thermal/15 border-thermal text-thermal hover:bg-thermal/25",
    };

    const sizeStyles = {
      sm: "w-7 h-7 text-xs",
      md: "w-8 h-8 text-sm",
      lg: "w-9 h-9 text-base",
    };

    return (
      <button
        ref={ref}
        aria-label={ariaLabel}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

IconButton.displayName = "IconButton";
