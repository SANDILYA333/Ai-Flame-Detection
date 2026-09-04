"use client";

import React, { useMemo } from "react";
import { AgniAudioTelemetry, AgniStatus } from "@/services/agni/agniTypes";
import { cn } from "@/lib/utils";

export interface AgniWaveformProps {
  status: AgniStatus;
  telemetry?: AgniAudioTelemetry;
  barsCount?: number;
  className?: string;
  height?: number;
}

export function AgniWaveform({
  status,
  telemetry,
  barsCount = 14,
  className,
  height = 36,
}: AgniWaveformProps) {
  // Check if real telemetry is feeding actively
  const hasRealAudio = useMemo(() => {
    return (
      telemetry &&
      (telemetry.amplitude > 0.02 ||
        telemetry.frequencies.some((f) => f > 0.05))
    );
  }, [telemetry]);

  // Generate bar heights based on state
  const bars = useMemo(() => {
    const arr: { heightPercent: number; isHot: boolean }[] = [];

    for (let i = 0; i < barsCount; i++) {
      let heightPercent = 12; // Base minimum height
      let isHot = false;

      if (status === "listening") {
        if (hasRealAudio && telemetry) {
          // Map real frequency telemetry across bars symmetrically
          const mid = barsCount / 2;
          const dist = Math.abs(i - mid) / mid;
          const freqIndex = Math.min(
            telemetry.frequencies.length - 1,
            Math.floor((1 - dist) * telemetry.frequencies.length)
          );
          const rawVal = telemetry.frequencies[freqIndex] || telemetry.amplitude;
          heightPercent = Math.min(100, Math.max(15, rawVal * 100));
          isHot = heightPercent > 75;
        } else {
          // Tactical animated simulation waveform if mic is silent/simulated
          const wavePhase = (i / barsCount) * Math.PI * 2;
          const sim = 20 + Math.abs(Math.sin(wavePhase)) * 55;
          heightPercent = sim;
        }
      } else if (status === "activating") {
        // Pulse towards center
        const mid = barsCount / 2;
        const dist = Math.abs(i - mid);
        heightPercent = Math.max(15, 60 - dist * 8);
      } else if (status === "processing") {
        // Scanning wave
        heightPercent = 30;
      } else if (status === "executing") {
        // Cascading pulse — each bar activates sequentially
        const phase = (i / barsCount) * Math.PI * 2;
        heightPercent = 20 + Math.abs(Math.sin(phase)) * 45;
        isHot = i % 2 === 0;
      } else if (status === "speaking") {
        // Rhythmic synthetic speaking waveform
        const wave = 25 + Math.abs(Math.sin((i / barsCount) * Math.PI * 3)) * 60;
        heightPercent = wave;
        isHot = i % 3 === 0;
      } else if (status === "error") {
        heightPercent = 20;
      } else {
        // Idle state: minimal resting bars
        heightPercent = 10;
      }

      arr.push({ heightPercent, isHot });
    }

    return arr;
  }, [status, hasRealAudio, telemetry, barsCount]);

  return (
    <div
      role="img"
      aria-label={`AGNI Voice Waveform — Status: ${status}`}
      className={cn(
        "relative flex items-center justify-center gap-1 w-full px-2 overflow-hidden select-none",
        className
      )}
      style={{ height: `${height}px` }}
    >
      {/* Background glow when active */}
      {(status === "listening" || status === "speaking" || status === "executing") && (
        <div className="absolute inset-0 bg-accent/5 rounded-control blur-sm pointer-events-none" />
      )}

      {/* Processing radar sweep overlay */}
      {(status === "processing" || status === "executing") && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-accent-cyan to-transparent animate-pulse" />
        </div>
      )}

      {/* Frequency / Equalizer Bars */}
      {bars.map((bar, idx) => {
        let barColor = "bg-border-strong";

        if (status === "listening") {
          barColor = bar.isHot
            ? "bg-accent shadow-[0_0_8px_rgba(57,255,136,0.6)]"
            : "bg-accent-cyan/80";
        } else if (status === "activating") {
          barColor = "bg-state-warning/80";
        } else if (status === "processing") {
          barColor = "bg-accent-cyan animate-pulse";
        } else if (status === "executing") {
          barColor = bar.isHot
            ? "bg-accent-cyan shadow-[0_0_6px_rgba(0,217,255,0.5)]"
            : "bg-accent-cyan/60";
        } else if (status === "speaking") {
          barColor = bar.isHot
            ? "bg-accent shadow-[0_0_6px_rgba(57,255,136,0.5)]"
            : "bg-accent/70";
        } else if (status === "error") {
          barColor = "bg-state-error/80";
        }

        return (
          <div
            key={idx}
            className="flex-1 max-w-[6px] rounded-pill transition-all duration-100 ease-out"
            style={{
              height: `${bar.heightPercent}%`,
              minHeight: "4px",
            }}
          >
            <div className={cn("w-full h-full rounded-pill", barColor)} />
          </div>
        );
      })}
    </div>
  );
}
