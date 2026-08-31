import React from "react";
import { cn } from "@/lib/utils";

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
  ariaLabel?: string;
}

export function Toggle({
  checked,
  onChange,
  disabled = false,
  size = "md",
  className,
  ariaLabel,
}: ToggleProps) {
  const isSm = size === "sm";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex shrink-0 cursor-pointer rounded-pill transition-all duration-150 ease-in-out focus:outline-none focus:ring-1 focus:ring-accent active:scale-95 disabled:opacity-40 disabled:pointer-events-none border select-none",
        isSm ? "h-4 w-7" : "h-5 w-9",
        checked
          ? "bg-accent/20 border-accent text-accent"
          : "bg-surface-raised border-border text-foreground-disabled",
        className
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block rounded-full bg-current transform transition duration-150 ease-in-out",
          isSm ? "h-2.5 w-2.5 mt-[2px]" : "h-3.5 w-3.5 mt-[2px]",
          checked
            ? isSm
              ? "translate-x-3.5 bg-accent"
              : "translate-x-4 bg-accent"
            : "translate-x-0.5 bg-foreground-muted"
        )}
      />
    </button>
  );
}
