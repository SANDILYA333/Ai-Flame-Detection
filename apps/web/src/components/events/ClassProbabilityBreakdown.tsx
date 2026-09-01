"use client";

import React from "react";
import type { ClassProbability } from "@/types/xai";
import { cn } from "@/lib/utils";

export interface ClassProbabilityBreakdownProps {
  probabilities: ClassProbability[];
  className?: string;
}

export function ClassProbabilityBreakdown({
  probabilities,
  className,
}: ClassProbabilityBreakdownProps) {
  if (!probabilities || probabilities.length === 0) return null;

  return (
    <div
      className={cn(
        "p-2.5 rounded-control bg-surface/80 border border-border/80 font-mono space-y-1.5",
        className
      )}
    >
      <div className="text-[10px] uppercase tracking-wider text-foreground-muted font-semibold flex items-center justify-between">
        <span>Calibrated Class Probabilities</span>
        <span className="text-[8.5px] text-foreground-muted/70">Sum: 100%</span>
      </div>

      <div className="space-y-1.5 pt-0.5">
        {probabilities.map((prob) => (
          <div key={prob.className} className="space-y-0.5">
            <div className="flex items-center justify-between text-[10px] text-foreground-secondary">
              <span className="font-medium">{prob.label}</span>
              <span className="font-semibold text-foreground">{prob.percentage}%</span>
            </div>
            <div className="w-full h-1.5 bg-background rounded-full overflow-hidden border border-border/40">
              <div
                className="h-full transition-all duration-300 rounded-full"
                style={{
                  width: `${prob.percentage}%`,
                  backgroundColor: prob.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
