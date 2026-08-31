import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger" | "thermal";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "secondary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-colors duration-150 rounded-control focus:outline-none focus:ring-1 focus:ring-accent focus:ring-offset-1 focus:ring-offset-background disabled:opacity-40 disabled:pointer-events-none select-none text-xs tracking-wider uppercase";

    const variantStyles = {
      primary:
        "bg-accent text-background hover:bg-emerald-400 font-semibold shadow-inset",
      secondary:
        "bg-surface text-foreground-secondary hover:text-foreground hover:bg-surface-hover border border-border",
      ghost:
        "text-foreground-secondary hover:text-foreground hover:bg-surface-hover",
      outline:
        "bg-transparent border border-border text-foreground hover:bg-surface-hover hover:border-border-strong",
      danger:
        "bg-state-error/20 text-state-error border border-state-error/40 hover:bg-state-error/30",
      thermal:
        "bg-thermal text-background font-semibold hover:bg-amber-500 shadow-thermal-glow",
    };

    const sizeStyles = {
      sm: "h-7 px-2.5 text-[11px] gap-1.5",
      md: "h-8 px-3.5 text-xs gap-2",
      lg: "h-9 px-4 text-xs gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {loading ? (
          <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin mr-1.5" />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);

Button.displayName = "Button";
