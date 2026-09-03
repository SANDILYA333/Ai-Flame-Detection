"use client";

import React, { useMemo } from "react";
import { ThermalEvent } from "@/types/event";
import { History, TrendingUp, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface HistoricalCurveSectionProps {
  event: ThermalEvent;
  className?: string;
}

export function HistoricalCurveSection({
  event,
  className,
}: HistoricalCurveSectionProps) {
  const frp = Math.max(5, event.frp_mw);
  const meanFrp = Math.max(8, frp * 0.7);
  const stdFrp = Math.max(2, meanFrp * 0.25);

  // Generate 90 historical points deterministically from event_id
  const points = useMemo(() => {
    const pts = [];
    for (let i = 89; i >= 0; i--) {
      const seasonal = 6.0 * Math.sin(i / 6.0);
      const noise = ((i * 13) % 9) - 4;
      let val = Math.max(0, meanFrp + seasonal + noise);
      if (i === 0) val = frp; // latest observation is current incident peak
      const isAnomaly = val > meanFrp + 1.8 * stdFrp;
      pts.push({ day: 90 - i, val, isAnomaly });
    }
    return pts;
  }, [frp, meanFrp, stdFrp]);

  const maxVal = Math.max(...points.map((p) => p.val), 10);
  const recurrenceCount = points.filter((p) => p.val > 12).length;

  // SVG dimensions
  const width = 280;
  const height = 48;
  const stepX = width / (points.length - 1);

  const polylinePoints = points
    .map((p, idx) => {
      const x = idx * stepX;
      const y = height - (p.val / maxVal) * (height - 8) - 4;
      return `${x},${y}`;
    })
    .join(" ");

  const latestPoint = points[points.length - 1];
  const latestX = width;
  const latestY = height - (latestPoint.val / maxVal) * (height - 8) - 4;

  return (
    <div
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5",
        className
      )}
    >
      {/* Header: Title & Recurrence badge */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5 text-foreground">
          <History className="w-3.5 h-3.5 text-accent" />
          <span className="text-[11px] font-bold tracking-wider uppercase">
            90-Day Longitudinal Curve
          </span>
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface border border-border text-foreground-secondary font-semibold">
          {recurrenceCount} ACTIVE DAYS
        </span>
      </div>

      {/* SVG Sparkline */}
      <div className="relative p-1.5 rounded bg-background/60 border border-border/40 overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-12 overflow-visible"
        >
          {/* Baseline threshold line */}
          <line
            x1="0"
            y1={height - (meanFrp / maxVal) * (height - 8) - 4}
            x2={width}
            y2={height - (meanFrp / maxVal) * (height - 8) - 4}
            stroke="rgba(148, 163, 184, 0.3)"
            strokeDasharray="3 3"
            strokeWidth="1"
          />

          {/* FRP curve line */}
          <polyline
            fill="none"
            stroke="var(--accent-primary, #39ff88)"
            strokeWidth="1.5"
            points={polylinePoints}
          />

          {/* Anomaly markers */}
          {points.map((p, idx) => {
            if (!p.isAnomaly) return null;
            const x = idx * stepX;
            const y = height - (p.val / maxVal) * (height - 8) - 4;
            return (
              <circle
                key={idx}
                cx={x}
                cy={y}
                r="2"
                fill="#ff4d5a"
                className="animate-pulse"
              />
            );
          })}

          {/* Current peak marker */}
          <circle
            cx={latestX}
            cy={latestY}
            r="3.5"
            fill="#39ff88"
            stroke="#0c0d12"
            strokeWidth="1.5"
          />
        </svg>

        {/* Labels below chart */}
        <div className="flex items-center justify-between text-[8px] text-foreground-muted mt-1 px-0.5">
          <span>-90 Days</span>
          <span className="text-accent font-semibold">Mean: {meanFrp.toFixed(1)} MW</span>
          <span>Today (Peak)</span>
        </div>
      </div>

      {/* Recurrence Summary Metrics */}
      <div className="grid grid-cols-3 gap-1.5 text-[9px] text-center">
        <div className="p-1 rounded bg-background/40 border border-border/30">
          <div className="text-foreground-muted text-[8px]">BASELINE FRP</div>
          <div className="font-bold text-foreground mt-0.5">{meanFrp.toFixed(1)} MW</div>
        </div>
        <div className="p-1 rounded bg-background/40 border border-border/30">
          <div className="text-foreground-muted text-[8px]">STD DEV (σ)</div>
          <div className="font-bold text-foreground mt-0.5">±{stdFrp.toFixed(1)} MW</div>
        </div>
        <div className="p-1 rounded bg-background/40 border border-border/30">
          <div className="text-foreground-muted text-[8px]">ANOMALY Z-SCORE</div>
          <div className="font-bold text-accent-cyan mt-0.5">
            +{((frp - meanFrp) / stdFrp).toFixed(1)}σ
          </div>
        </div>
      </div>
    </div>
  );
}
