"use client";

import React, { useEffect } from "react";
import { AgniButton } from "./AgniButton";
import { AgniPanel } from "./AgniPanel";
import { useAgni } from "@/hooks/useAgni";
import { cn } from "@/lib/utils";

export interface AgniAssistantProps {
  className?: string;
  onOpenSimLab?: () => void;
  setViewMode?: (mode: "2D" | "3D") => void;
  setBasemap?: (basemap: string) => void;
  centerMap?: () => void;
}

export function AgniAssistant({
  className,
  onOpenSimLab,
  setViewMode,
  setBasemap,
  centerMap,
}: AgniAssistantProps) {
  const agni = useAgni({
    autoStartOnOpen: true,
    onOpenSimLab,
    setViewMode,
    setBasemap,
    centerMap,
  });

  // Global Keyboard Shortcut: Alt+A / Option+A to toggle AGNI
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input/textarea
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }

      if (e.altKey && e.key.toLowerCase() === "a") {
        e.preventDefault();
        agni.toggleAgni();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [agni]);

  return (
    <div className={cn("relative inline-flex items-center", className)}>
      {/* 1. Header Trigger Button */}
      <AgniButton
        status={agni.status}
        isOpen={agni.isOpen}
        onClick={agni.toggleAgni}
      />

      {/* 2. Tactical Floating Overlay Panel */}
      <AgniPanel
        status={agni.status}
        isOpen={agni.isOpen}
        transcript={agni.transcript}
        response={agni.response}
        error={agni.error}
        audioTelemetry={agni.audioTelemetry}
        context={agni.context}
        demoPresets={agni.demoPresets}
        isMuted={agni.isMuted}
        onToggleMute={agni.toggleMute}
        onClose={agni.closeAgni}
        onStartListening={agni.startListening}
        onStopListening={agni.stopListening}
        onRetryListening={agni.retryListening}
        onDismissError={agni.dismissError}
        onExecuteDemoPreset={agni.executeDemoPreset}
        onSubmitTextCommand={agni.submitTextCommand}
      />
    </div>
  );
}
