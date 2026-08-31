"use client";

import React, { useMemo } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Clock,
  Flame,
  Radio,
  FastForward,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import {
  formatTimelineStamp,
  formatTimelineAxisLabel,
} from "@/lib/playback/temporal";
import type { PlaybackSpeed, TimeWindow } from "@/types/playback";
import { cn } from "@/lib/utils";

export interface TimelinePlaybackBarProps {
  className?: string;
}

const TIME_WINDOWS: TimeWindow[] = ["1H", "6H", "24H", "48H", "7D", "ALL"];
const SPEEDS: PlaybackSpeed[] = [1, 2, 4, 8];

export function TimelinePlaybackBar({ className }: TimelinePlaybackBarProps) {
  const {
    timeRange,
    setTimeRange,
    playbackMode,
    isPlaying,
    playbackSpeed,
    playbackTime,
    playbackRange,
    playbackProgress,
    setPlaybackProgress,
    setPlaybackSpeed,
    togglePlayPause,
    stepForward,
    stepBackward,
    resetToLive,
    filteredEvents,
    rawEvents,
  } = useEventContext();

  const isLive = playbackMode === "LIVE";
  const startLabel = useMemo(
    () => formatTimelineAxisLabel(playbackRange.start),
    [playbackRange.start]
  );
  const endLabel = useMemo(
    () => formatTimelineAxisLabel(playbackRange.end),
    [playbackRange.end]
  );
  const currentStamp = useMemo(
    () => formatTimelineStamp(playbackTime),
    [playbackTime]
  );

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (!isNaN(val)) {
      setPlaybackProgress(val);
    }
  };

  return (
    <div
      className={cn(
        "pointer-events-auto select-none font-mono bg-surface-raised/95 backdrop-blur-md border border-border rounded-panel shadow-panel px-3.5 py-2.5 flex flex-col gap-2 transition-all duration-200",
        className
      )}
    >
      {/* 1. Top Control Bar: Mode Badge, Window Selector, Transport, Speed */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Mode Indicator & Window Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mode Pill */}
          <button
            onClick={() => {
              if (isLive) {
                togglePlayPause();
              } else {
                resetToLive();
              }
            }}
            title={isLive ? "Click to start Temporal Playback" : "Click to return to LIVE mode"}
            className={cn(
              "h-7 px-2.5 rounded-control text-[10px] font-bold border flex items-center gap-1.5 transition-all shadow-sm",
              isLive
                ? "bg-state-success/15 border-state-success/40 text-state-success hover:bg-state-success/25"
                : "bg-accent/15 border-accent/40 text-accent hover:bg-accent/25"
            )}
          >
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                isLive ? "bg-state-success animate-pulse" : "bg-accent animate-ping-once"
              )}
            />
            <span>{isLive ? "LIVE STREAM" : "TEMPORAL PLAYBACK"}</span>
          </button>

          {/* Time Window Buttons */}
          <div className="flex items-center bg-surface border border-border/80 rounded-control p-0.5">
            {TIME_WINDOWS.map((win) => {
              const isSelected =
                timeRange.toUpperCase() === win.toUpperCase() ||
                (win === "ALL" && timeRange.toUpperCase() === "ALL");
              return (
                <button
                  key={win}
                  onClick={() => setTimeRange(win)}
                  className={cn(
                    "h-6 px-2 text-[10px] font-semibold rounded-control transition-colors",
                    isSelected
                      ? "bg-accent text-bg-base shadow-sm"
                      : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
                  )}
                >
                  {win}
                </button>
              );
            })}
          </div>
        </div>

        {/* Transport Controls & Playhead Info */}
        <div className="flex items-center gap-2">
          {/* Transport Buttons */}
          <div className="flex items-center gap-1 bg-surface border border-border/80 rounded-control p-0.5">
            <button
              onClick={() => stepBackward(0.05)}
              title="Step Backward (5%)"
              aria-label="Step Backward"
              className="w-6 h-6 flex items-center justify-center rounded-control text-foreground-muted hover:text-foreground hover:bg-surface-hover active:scale-95 transition-all"
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={togglePlayPause}
              title={isPlaying ? "Pause Playback" : "Play Timeline"}
              aria-label={isPlaying ? "Pause" : "Play"}
              className="h-6 px-2.5 flex items-center gap-1 rounded-control bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30 active:scale-95 font-bold text-[10px] transition-all"
            >
              {isPlaying ? (
                <>
                  <Pause className="w-3 h-3" />
                  <span>PAUSE</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3" />
                  <span>PLAY</span>
                </>
              )}
            </button>

            <button
              onClick={() => stepForward(0.05)}
              title="Step Forward (5%)"
              aria-label="Step Forward"
              className="w-6 h-6 flex items-center justify-center rounded-control text-foreground-muted hover:text-foreground hover:bg-surface-hover active:scale-95 transition-all"
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>

            {!isLive && (
              <button
                onClick={resetToLive}
                title="Jump to Live Stream"
                aria-label="Jump to Live"
                className="h-6 px-1.5 flex items-center gap-1 rounded-control text-state-success hover:bg-state-success/15 text-[10px] font-semibold transition-all"
              >
                <RotateCcw className="w-3 h-3" />
                <span className="hidden sm:inline">LIVE</span>
              </button>
            )}
          </div>

          {/* Playback Speed Multiplier */}
          <div className="flex items-center bg-surface border border-border/80 rounded-control p-0.5">
            {SPEEDS.map((spd) => (
              <button
                key={spd}
                onClick={() => setPlaybackSpeed(spd)}
                className={cn(
                  "h-6 px-1.5 text-[9px] font-bold rounded-control transition-colors",
                  playbackSpeed === spd
                    ? "bg-accent-cyan/25 text-accent-cyan border border-accent-cyan/40"
                    : "text-foreground-muted hover:text-foreground"
                )}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Interactive Scrubber Bar & Timestamp Axis */}
      <div className="space-y-1">
        <div className="relative flex items-center">
          <input
            type="range"
            min="0"
            max="1"
            step="0.001"
            value={playbackProgress}
            onChange={handleSliderChange}
            className="w-full h-1.5 bg-background rounded-full appearance-none cursor-pointer accent-accent focus:outline-none border border-border/50"
          />
        </div>

        {/* Axis Labels & Current Playhead Metric */}
        <div className="flex items-center justify-between text-[9px] text-foreground-muted font-mono">
          <span className="truncate max-w-[120px]">{startLabel}</span>

          <div className="flex items-center gap-2 text-foreground font-semibold px-2 py-0.5 rounded bg-surface border border-border/60">
            <Clock className="w-2.5 h-2.5 text-accent-cyan" />
            <span>{currentStamp}</span>
            <span className="text-border-strong">|</span>
            <span className="text-thermal-primary flex items-center gap-0.5">
              <Flame className="w-2.5 h-2.5" />
              {filteredEvents.length} / {rawEvents.length} Anomaly Events
            </span>
          </div>

          <span className="truncate max-w-[120px] text-right">{endLabel}</span>
        </div>
      </div>
    </div>
  );
}
