"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  MicOff,
  X,
  Radio,
  Sparkles,
  RefreshCw,
  CornerDownLeft,
  ChevronDown,
  ChevronUp,
  Sliders,
  Terminal,
  Volume2,
  VolumeX,
  Loader2,
} from "lucide-react";
import { AgniStatus } from "./AgniStatus";
import { AgniWaveform } from "./AgniWaveform";
import type {
  AgniAudioTelemetry,
  AgniContext,
  AgniError,
  AgniResponse,
  AgniStatus as StatusType,
  AgniTranscript,
} from "@/services/agni/agniTypes.ts";
import type { AgniDemoPreset } from "@/services/agni/agniService.ts";
import { cn } from "@/lib/utils";

export interface AgniPanelProps {
  status: StatusType;
  isOpen: boolean;
  transcript: AgniTranscript | null;
  response: AgniResponse | null;
  error: AgniError | null;
  audioTelemetry: AgniAudioTelemetry;
  context: AgniContext;
  demoPresets: AgniDemoPreset[];
  isMuted?: boolean;
  onClose: () => void;
  onToggleMute?: () => void;
  onStartListening: () => Promise<void>;
  onStopListening: () => void;
  onRetryListening: () => Promise<void>;
  onDismissError: () => void;
  onExecuteDemoPreset: (preset: AgniDemoPreset) => Promise<void>;
  onSubmitTextCommand: (text: string) => Promise<void>;
  className?: string;
}

export function AgniPanel({
  status,
  isOpen,
  transcript,
  response,
  error,
  audioTelemetry,
  context,
  demoPresets,
  isMuted = false,
  onClose,
  onToggleMute,
  onStartListening,
  onStopListening,
  onRetryListening,
  onDismissError,
  onExecuteDemoPreset,
  onSubmitTextCommand,
  className,
}: AgniPanelProps) {
  const [inputText, setInputText] = useState("");
  const [showPresets, setShowPresets] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const isListening = status === "listening";
  const isProcessing = status === "processing";
  const isExecuting = status === "executing";
  const isSpeaking = status === "speaking";
  const isError = status === "error";
  const isBusy = isProcessing || isExecuting;

  // Handle escape key to close panel
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSubmitTextCommand(inputText.trim());
    setInputText("");
  };

  return (
    <div
      id="agni-console-panel"
      role="region"
      aria-label="AGNI Voice Intelligence Console"
      className={cn(
        "absolute top-14 right-3 z-40 w-96 max-w-[calc(100vw-24px)] bg-surface-raised/95 backdrop-blur-md border border-accent/40 rounded-panel shadow-panel-glow flex flex-col font-sans overflow-hidden animate-in fade-in zoom-in-95 duration-150 select-none",
        className
      )}
    >
      {/* 1. Header & Identity */}
      <div className="h-10 px-3.5 bg-surface border-b border-border flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-control bg-accent/20 border border-accent/40 flex items-center justify-center text-accent">
            {isSpeaking ? (
              <Volume2 className="w-3 h-3 text-accent animate-pulse" />
            ) : (
              <Radio className={cn("w-3 h-3 text-accent", isListening && "animate-pulse")} />
            )}
          </div>
          <span className="text-xs font-bold font-mono tracking-wider text-foreground">
            AGNI
          </span>
          <span className="text-[10px] font-mono text-foreground-muted hidden sm:inline">
            VOICE INTELLIGENCE
          </span>
        </div>

        <div className="flex items-center gap-2">
          <AgniStatus status={status} />

          {onToggleMute && (
            <button
              type="button"
              onClick={onToggleMute}
              title={isMuted ? "Unmute Voice Response" : "Mute Voice Response"}
              aria-label={isMuted ? "Unmute Voice Response" : "Mute Voice Response"}
              className="w-6 h-6 rounded-control hover:bg-surface-hover flex items-center justify-center text-foreground-muted hover:text-foreground transition-colors"
            >
              {isMuted ? (
                <VolumeX className="w-3.5 h-3.5 text-state-warning" />
              ) : (
                <Volume2 className="w-3.5 h-3.5 text-accent" />
              )}
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            aria-label="Close AGNI console"
            className="w-6 h-6 rounded-control hover:bg-surface-hover flex items-center justify-center text-foreground-muted hover:text-foreground transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Waveform & Voice Activity Visualizer */}
      <div className="p-3 bg-surface/40 border-b border-border flex flex-col gap-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-foreground-muted">
          <span className="flex items-center gap-1">
            <Terminal className="w-3 h-3 text-accent-cyan" />
            <span>SPECTRAL TELEMETRY</span>
          </span>
          <span>
            {isListening
              ? `${Math.round(audioTelemetry.amplitude * 100)}% AMP`
              : isSpeaking
              ? "TTS ACTIVE"
              : isExecuting
              ? "DISPATCHING"
              : status.toUpperCase()}
          </span>
        </div>

        {/* Audio Waveform */}
        <div className="bg-bg-base/80 rounded-control p-2 border border-border flex items-center justify-center">
          <AgniWaveform
            status={status}
            telemetry={audioTelemetry}
            barsCount={16}
            height={38}
          />
        </div>

        {/* Mic Controls Row */}
        <div className="flex items-center justify-between gap-2 mt-1">
          <button
            type="button"
            onClick={isListening || isSpeaking ? onStopListening : onStartListening}
            disabled={isBusy}
            aria-label={isListening ? "Stop listening" : isSpeaking ? "Stop speaking" : "Start listening"}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-control text-xs font-mono font-bold transition-all",
              isListening || isSpeaking
                ? "bg-state-warning/15 hover:bg-state-warning/25 border border-state-warning/40 text-state-warning"
                : "bg-accent/15 hover:bg-accent/25 border border-accent/40 text-accent",
              isBusy && "opacity-50 cursor-not-allowed"
            )}
          >
            {isSpeaking ? (
              <>
                <VolumeX className="w-3.5 h-3.5" />
                <span>STOP SPEAKING</span>
              </>
            ) : isListening ? (
              <>
                <MicOff className="w-3.5 h-3.5" />
                <span>STOP LISTENING</span>
              </>
            ) : (
              <>
                <Mic className="w-3.5 h-3.5" />
                <span>START LISTENING</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3. Error Banner (if any) */}
      {isError && error && (
        <div className="p-3 bg-state-error/15 border-b border-state-error/30 flex flex-col gap-2 text-xs font-mono">
          <div className="flex items-center justify-between text-state-error font-bold">
            <span>{error.message}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-state-error/20">
              {error.code}
            </span>
          </div>
          {error.technicalDetails && (
            <div className="text-[10px] text-foreground-muted leading-relaxed font-sans">
              {error.technicalDetails}
            </div>
          )}
          <div className="flex items-center gap-2 mt-1">
            {error.retryable && (
              <button
                type="button"
                onClick={onRetryListening}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-state-error/25 border border-state-error/40 text-state-error hover:bg-state-error/35 font-bold transition-colors text-[11px]"
              >
                <RefreshCw className="w-3 h-3" />
                <span>RETRY ACCESS</span>
              </button>
            )}
            <button
              type="button"
              onClick={onDismissError}
              className="px-2 py-1 rounded bg-surface hover:bg-surface-hover border border-border text-foreground-muted text-[11px] transition-colors"
            >
              DISMISS
            </button>
          </div>
        </div>
      )}

      {/* 4. Transcribed Command & AGNI Response Area */}
      <div className="p-3.5 flex flex-col gap-3 max-h-56 overflow-y-auto">
        {/* Operator Intent — Live/Final Transcript */}
        {transcript ? (
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-[10px] font-mono text-accent-cyan">
              <span className="flex items-center gap-1.5">
                <span>OPERATOR INTENT</span>
                {/* Live/Final indicator */}
                {transcript.isFinal ? (
                  <span className="px-1 py-0.5 rounded bg-accent/20 text-accent text-[9px] font-bold">
                    FINAL
                  </span>
                ) : (
                  <span className="px-1 py-0.5 rounded bg-accent-cyan/20 text-accent-cyan text-[9px] font-bold flex items-center gap-0.5">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-cyan opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-cyan" />
                    </span>
                    LIVE
                  </span>
                )}
              </span>
              <span>{transcript.source.toUpperCase()}</span>
            </div>
            <div
              className={cn(
                "p-2.5 rounded-control bg-surface border border-border text-xs font-sans leading-relaxed transition-all",
                transcript.isFinal
                  ? "text-foreground font-medium"
                  : "text-foreground-muted italic"
              )}
            >
              &ldquo;{transcript.text}&rdquo;
              {!transcript.isFinal && (
                <span className="inline-block w-0.5 h-3.5 bg-accent-cyan ml-0.5 animate-pulse align-text-bottom" />
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-2 text-xs font-mono text-foreground-muted">
            {isListening
              ? "Listening for operational voice command..."
              : isBusy
              ? "Processing command..."
              : "Ready. Click Start Listening or choose a command."}
          </div>
        )}

        {/* Processing / Executing Indicator */}
        {(isProcessing || isExecuting) && (
          <div className="flex items-center gap-2 py-1 text-[10px] font-mono text-accent-cyan animate-in fade-in duration-200">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>
              {isProcessing ? "GEMINI INTERPRETING COMMAND..." : "EXECUTING OPERATIONAL ACTIONS..."}
            </span>
          </div>
        )}

        {/* AGNI Response Preview */}
        {response && (
          <div className="flex flex-col gap-1.5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between text-[10px] font-mono text-accent">
              <span className="flex items-center gap-1 font-bold">
                <Sparkles className="w-3 h-3" />
                <span>AGNI DISPATCH</span>
                {isSpeaking && (
                  <Volume2 className="w-3 h-3 ml-0.5 text-accent animate-pulse" />
                )}
              </span>
              <div className="flex items-center gap-1.5">
                {response.confidence !== undefined && (
                  <span className="text-[9px] px-1 py-0.2 rounded bg-accent/20 text-accent font-bold">
                    {Math.round(response.confidence * 100)}% CONF
                  </span>
                )}
                {response.actionTaken && (
                  <span className="text-foreground-muted text-[9px] font-semibold">
                    {response.actionTaken}
                  </span>
                )}
              </div>
            </div>

            <div className="p-2.5 rounded-control bg-accent/10 border border-accent/30 text-xs text-accent font-sans leading-relaxed font-medium">
              {response.text}
            </div>

            {/* Execution Trace Badges */}
            {response.command?.executionTrace && response.command.executionTrace.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-0.5">
                {response.command.executionTrace.map((traceItem, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface border border-accent/30 text-accent-cyan"
                  >
                    <span>✓</span>
                    <span>{traceItem}</span>
                  </span>
                ))}
              </div>
            )}

            {/* Consequential Action / Dispatch Preview Confirmation Card */}
            {response.command?.isConsequential && (
              <div className="p-2 rounded bg-state-warning/10 border border-state-warning/30 flex flex-col gap-2 mt-1">
                <div className="text-[11px] font-mono text-state-warning font-bold flex items-center gap-1">
                  <span>⚠️</span>
                  <span>CONSEQUENTIAL ACTION REVIEW</span>
                </div>
                <div className="text-[10px] text-foreground-muted leading-relaxed font-sans">
                  Target: {response.command.targetIncidentId || response.command.targetCriterion || "Selected Incident"}.
                  Simulated dispatch protocol ready.
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onSubmitTextCommand("confirm")}
                    className="flex-1 px-2.5 py-1 rounded bg-state-warning/20 border border-state-warning/40 text-state-warning hover:bg-state-warning/30 text-[11px] font-mono font-bold transition-colors text-center"
                  >
                    REVIEW & PROCEED
                  </button>
                  <button
                    type="button"
                    onClick={() => onSubmitTextCommand("cancel")}
                    className="px-2.5 py-1 rounded bg-surface hover:bg-surface-hover border border-border text-foreground-muted text-[11px] font-mono transition-colors"
                  >
                    CANCEL
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. Direct Text Command Input */}
      <form
        onSubmit={handleFormSubmit}
        className="px-3 py-2 bg-surface/60 border-t border-border flex items-center gap-1.5"
      >
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type command or query..."
          disabled={isBusy}
          className="flex-1 bg-[#0b1015] text-[#f2f5f7] border border-[#252c35] px-2.5 py-1.5 rounded text-xs font-mono placeholder:text-[#737e89] caret-[#39ff88] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 selection:bg-accent/30 selection:text-white disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isBusy}
          aria-label="Send command"
          className="px-2 py-1 bg-accent/15 hover:bg-accent/25 border border-accent/40 text-accent disabled:opacity-40 rounded text-xs font-mono font-bold flex items-center justify-center transition-colors"
        >
          <CornerDownLeft className="w-3.5 h-3.5" />
        </button>
      </form>

      {/* 6. Tactical Verification Presets (Demo Mode) */}
      <div className="border-t border-border bg-surface/30">
        <button
          type="button"
          onClick={() => setShowPresets(!showPresets)}
          className="w-full px-3 py-1.5 flex items-center justify-between text-[10px] font-mono text-foreground-muted hover:text-foreground hover:bg-surface-hover/40 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Sliders className="w-3 h-3 text-accent-cyan" />
            <span>TACTICAL OPERATIONAL PRESETS</span>
          </span>
          {showPresets ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </button>

        {showPresets && (
          <div className="p-2.5 pt-1 grid grid-cols-1 gap-1.5 bg-bg-base/40 max-h-48 overflow-y-auto scrollbar-thin">
            {demoPresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => onExecuteDemoPreset(preset)}
                disabled={isBusy}
                className="text-left px-2.5 py-1.5 rounded bg-surface hover:bg-surface-hover border border-border hover:border-accent/40 text-xs font-mono text-foreground-secondary hover:text-accent transition-all flex items-center justify-between group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="truncate">{preset.label}</span>
                <span className="text-[9px] text-foreground-muted group-hover:text-accent/80 shrink-0 ml-1">
                  EXECUTE
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 7. Live Context Telemetry Footer */}
      <div className="px-3 py-1.5 bg-bg-base border-t border-border flex items-center justify-between text-[9px] font-mono text-foreground-muted shrink-0">
        <span>
          CONTEXT: {context.visibleEventCount}/{context.totalEventCount} EVTS
        </span>
        <span>
          CLASS: {context.activeFilters.classification} · {context.playbackMode}
        </span>
      </div>
    </div>
  );
}
