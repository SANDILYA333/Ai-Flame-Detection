/**
 * AGNI — AI Voice Intelligence Assistant
 * Phase 3: State Machine, Web Speech Live STT, TTS Speech Synthesis & Gemini Command Execution Hook
 */

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import type {
  AgniAction,
  AgniActionHandlers,
  AgniAudioTelemetry,
  AgniContext,
  AgniError,
  AgniFilters,
  AgniResponse,
  AgniStatus,
  AgniStructuredCommand,
  AgniTranscript,
} from "@/services/agni/agniTypes.ts";
import {
  agniService,
  AgniDemoPreset,
  AGNI_DEMO_PRESETS,
} from "@/services/agni/agniService.ts";
import { useEventContext } from "@/context/EventContext";

export interface UseAgniOptions {
  autoStartOnOpen?: boolean;
  onOpenSimLab?: () => void;
  setViewMode?: (mode: "2D" | "3D") => void;
  setBasemap?: (basemap: string) => void;
  centerMap?: () => void;
}

export interface UseAgniReturn {
  // State Machine
  status: AgniStatus;
  isOpen: boolean;
  transcript: AgniTranscript | null;
  response: AgniResponse | null;
  error: AgniError | null;
  audioTelemetry: AgniAudioTelemetry;
  context: AgniContext;
  demoPresets: AgniDemoPreset[];
  isSpeechRecognitionSupported: boolean;
  isMuted: boolean;

  // Actions & Controls
  openAgni: () => void;
  closeAgni: () => void;
  toggleAgni: () => void;
  toggleMute: () => void;
  startListening: () => Promise<void>;
  stopListening: () => void;
  dismissError: () => void;
  retryListening: () => Promise<void>;
  processTranscript: (text: string, source?: "microphone" | "demo" | "simulated") => Promise<void>;
  executeDemoPreset: (preset: AgniDemoPreset) => Promise<void>;
  submitTextCommand: (text: string) => Promise<void>;
  executeStructuredCommand: (command: AgniStructuredCommand) => Promise<boolean>;
  executeRawAction: (action: AgniAction) => Promise<boolean>;
}

export function useAgni(options: UseAgniOptions = {}): UseAgniReturn {
  const { autoStartOnOpen = true, onOpenSimLab, setViewMode, setBasemap, centerMap } = options;

  const [status, setStatus] = useState<AgniStatus>("idle");
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<AgniTranscript | null>(null);
  const [response, setResponse] = useState<AgniResponse | null>(null);
  const [error, setError] = useState<AgniError | null>(null);
  const [lastCommand, setLastCommand] = useState<AgniStructuredCommand | undefined>(undefined);
  const [lastFilters, setLastFilters] = useState<AgniFilters | undefined>(undefined);
  const [audioTelemetry, setAudioTelemetry] = useState<AgniAudioTelemetry>({
    amplitude: 0,
    frequencies: [0, 0, 0, 0, 0, 0, 0, 0],
  });

  const animFrameRef = useRef<number | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Check speech recognition support
  const isSpeechRecognitionSupported = useMemo(() => {
    if (typeof window === "undefined") return false;
    return Boolean(
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    );
  }, []);

  // Consume canonical EventContext
  const eventContext = useEventContext();

  // Map state mutators to AgniActionHandlers
  const actionHandlers = useMemo<AgniActionHandlers>(() => {
    return {
      setClassification: eventContext?.setSelectedClassification,
      setPriority: eventContext?.setSelectedPriority,
      setTimeRange: eventContext?.setTimeRange,
      setSearchQuery: eventContext?.setSearchQuery,
      selectEvent: (eventId: string) => {
        const found = eventContext?.rawEvents.find((e) => e.event_id === eventId);
        if (found) {
          eventContext?.setSelectedEvent(found);
          eventContext?.setIsDetailOpen(true);
        }
      },
      selectEventByCriterion: (criterion: string) => {
        if (!eventContext || eventContext.filteredEvents.length === 0) return;
        const events = [...eventContext.filteredEvents];
        if (criterion === "most_severe" || criterion === "highest_frp") {
          events.sort((a, b) => {
            const isIndustrialA = a.classification === "INDUSTRIAL" ? 2 : 1;
            const isIndustrialB = b.classification === "INDUSTRIAL" ? 2 : 1;
            if (isIndustrialA !== isIndustrialB) return isIndustrialB - isIndustrialA;
            return (b.frp_mw || 0) - (a.frp_mw || 0);
          });
        }
        const target = events[0];
        if (target) {
          eventContext.setSelectedEvent(target);
          eventContext.setIsDetailOpen(true);
        }
      },
      toggleLayer: (layerId: string, enabled?: boolean) => {
        if (eventContext) {
          if (enabled !== undefined) {
            if (eventContext.activeLayers[layerId] !== enabled) {
              eventContext.toggleLayer(layerId);
            }
          } else {
            eventContext.toggleLayer(layerId);
          }
        }
      },
      resetFilters: eventContext?.resetFilters,
      openSimLab: onOpenSimLab,
      setViewMode,
      setBasemap,
      centerMap: () => {
        if (centerMap) {
          centerMap();
        } else if (eventContext?.selectedEvent) {
          eventContext.setIsDetailOpen(true);
        }
      },
      openXai: () => {
        if (eventContext && !eventContext.selectedEvent && eventContext.filteredEvents.length > 0) {
          eventContext.setSelectedEvent(eventContext.filteredEvents[0]);
        }
        eventContext?.setIsDetailOpen(true);
        setTimeout(() => {
          const el = document.getElementById("xai-evidence-section");
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
      },
      showResponders: () => {
        if (eventContext && !eventContext.selectedEvent && eventContext.filteredEvents.length > 0) {
          eventContext.setSelectedEvent(eventContext.filteredEvents[0]);
        }
        eventContext?.toggleLayer("india-emergency-services");
        eventContext?.setIsDetailOpen(true);
      },
      showHazard: () => {
        if (eventContext && !eventContext.selectedEvent && eventContext.filteredEvents.length > 0) {
          eventContext.setSelectedEvent(eventContext.filteredEvents[0]);
        }
        eventContext?.setIsDetailOpen(true);
        setTimeout(() => {
          const el = document.getElementById("wind-intelligence-detail");
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
      },
      openDossier: () => {
        if (eventContext) {
          if (!eventContext.selectedEvent && eventContext.filteredEvents.length > 0) {
            eventContext.setSelectedEvent(eventContext.filteredEvents[0]);
          }
          eventContext.setIsDossierOpen(true);
          eventContext.setIsDetailOpen(true);
        }
      },
    };
  }, [eventContext, onOpenSimLab, setViewMode, setBasemap, centerMap]);


  // Derive contextual snapshot for AGNI
  const context = useMemo<AgniContext>(() => {
    return {
      selectedEventId: eventContext?.selectedEvent?.event_id,
      selectedEventSummary: eventContext?.selectedEvent?.context_summary,
      lastCommand,
      lastIntent: lastCommand?.intent,
      lastFilters,
      activeFilters: {
        classification: eventContext?.selectedClassification || "ALL",
        priority: eventContext?.selectedPriority || "ALL",
        timeRange: eventContext?.timeRange || "ALL",
        searchQuery: eventContext?.searchQuery || "",
      },
      activeLayers: eventContext?.activeLayers || {},
      visibleEventCount: eventContext?.filteredEvents?.length || 0,
      totalEventCount: eventContext?.rawEvents?.length || 0,
      isLiveBackend: Boolean(eventContext?.isLiveBackend),
      playbackMode: eventContext?.playbackMode || "LIVE",
      isPlaybackPlaying: Boolean(eventContext?.isPlaying),
      currentCoordinates: eventContext?.selectedEvent
        ? {
            lat: eventContext.selectedEvent.latitude,
            lon: eventContext.selectedEvent.longitude,
          }
        : undefined,
    };
  }, [eventContext, lastCommand, lastFilters]);

  // Audio Telemetry Poller loop during listening
  useEffect(() => {
    if (status === "listening") {
      let isSubscribed = true;

      const pollTelemetry = () => {
        if (!isSubscribed) return;
        const telem = agniService.getAudioTelemetry();
        setAudioTelemetry(telem);
        animFrameRef.current = requestAnimationFrame(pollTelemetry);
      };

      animFrameRef.current = requestAnimationFrame(pollTelemetry);

      return () => {
        isSubscribed = false;
        if (animFrameRef.current) {
          cancelAnimationFrame(animFrameRef.current);
        }
      };
    } else {
      setAudioTelemetry({
        amplitude: 0,
        frequencies: [0, 0, 0, 0, 0, 0, 0, 0],
      });
    }
  }, [status]);

      // Clean up resources on unmount
  useEffect(() => {
    return () => {
      agniService.stopAudioCapture();
      agniService.stopSpeechRecognition();
      agniService.stopSpeechSynthesis?.();
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  /**
   * Process and interpret natural language transcript with Gemini
   */
  const processTranscript = useCallback(
    async (text: string, source: "microphone" | "demo" | "simulated" = "microphone") => {
      if (!text.trim()) return;

      if (timeoutRef.current) clearTimeout(timeoutRef.current);

      const trimmedText = text.trim();

      // Quick check for verbal cancellation
      if (["stop", "cancel", "halt", "abort", "quiet"].includes(trimmedText.toLowerCase())) {
        agniService.stopSpeechRecognition();
        agniService.stopAudioCapture();
        agniService.stopSpeechSynthesis?.();
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setTranscript({
          id: `trans-${Date.now()}`,
          text: trimmedText,
          timestamp: Date.now(),
          source,
          isFinal: true,
        });
        setResponse({
          id: `resp-${Date.now()}`,
          text: "Command cancelled. Returning to idle.",
          timestamp: Date.now(),
          actionTaken: "CANCEL_ACTION",
          intent: "CANCEL_ACTION",
          status: "info",
          executionTrace: ["Operation → Cancelled"],
        });
        setStatus("idle");
        return;
      }

      setTranscript({
        id: `trans-${Date.now()}`,
        text: trimmedText,
        timestamp: Date.now(),
        source,
        isFinal: true,
      });

      // Stop listening stream
      agniService.stopSpeechRecognition();
      agniService.stopAudioCapture();
      setStatus("processing");

      // Invoke Gemini backend interpreter with contextual memory
      const result = await agniService.interpretTranscript(trimmedText, context);

      setStatus("executing");

      // Execute structured command in application state
      const success = await agniService.executeStructuredCommand(
        result.command,
        actionHandlers
      );

      // Retain conversational context
      if (result.command.filters) {
        setLastCommand(result.command);
        setLastFilters((prev) => ({
          ...prev,
          ...result.command.filters,
        }));
      }

      // Dynamic count-based response synthesis if filtered
      let responseText = result.message;
      if (
        result.command.intent === "FILTER_THERMAL_EVENTS" ||
        result.command.intent === "FILTER_THERMAL_ANOMALIES"
      ) {
        const matchingCount = eventContext?.filteredEvents?.length ?? 0;
        if (matchingCount === 0 && !result.command.requiresConfirmation) {
          responseText = "I couldn't find any industrial thermal anomalies matching those filters.";
        }
      }

      // Transition to speaking with response
      const resp: AgniResponse = {
        id: `resp-${Date.now()}`,
        text: responseText,
        timestamp: Date.now(),
        actionTaken: result.command.intent,
        intent: result.command.intent,
        confidence: result.command.confidence,
        status: success ? "success" : result.status === "ambiguous" ? "warning" : "info",
        executionLatencyMs: result.executionLatencyMs,
        executionTrace: result.command.executionTrace || [],
        isConsequential: result.command.isConsequential,
        requiresConfirmation: result.command.requiresConfirmation,
        command: result.command,
      };

      setResponse(resp);

      // Natural Voice Verbal Confirmation via Web Speech Synthesis (TTS)
      if (!isMuted && !result.command.requiresConfirmation && responseText.trim()) {
        setStatus("speaking");
        const spoken = agniService.speakText(responseText, {
          onStart: () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            setStatus("speaking");
          },
          onEnd: () => {
            setStatus("idle");
          },
          onError: (err) => {
            console.warn("[AGNI:TTS] Speech ended with error:", err);
            setStatus("idle");
          },
        });

        // Safety fallback: auto-reset to idle if browser drops TTS events
        if (spoken) {
          timeoutRef.current = setTimeout(() => {
            setStatus("idle");
          }, 8000);
        } else {
          timeoutRef.current = setTimeout(() => {
            setStatus("idle");
          }, 2500);
        }
      } else {
        timeoutRef.current = setTimeout(() => {
          setStatus("idle");
        }, 2500);
      }
    },
    [context, actionHandlers, isMuted, eventContext]
  );

  /**
   * Start Listening Flow: request mic + start speech recognition
   */
  const startListening = useCallback(async () => {
    setError(null);
    setStatus("activating");

    try {
      await agniService.startAudioCapture();
      setStatus("listening");

      // Start Web Speech API speech-to-text
      agniService.startSpeechRecognition({
        onTranscript: (text, isFinal) => {
          setTranscript({
            id: `trans-${Date.now()}`,
            text,
            timestamp: Date.now(),
            source: "microphone",
            isFinal,
          });

          if (isFinal) {
            processTranscript(text, "microphone");
          }
        },
        onError: (err) => {
          // If speech recognition throws non-fatal error, keep audio visualizer running
          if (err.code === "PERMISSION_DENIED") {
            setStatus("error");
            setError(err);
          }
        },
      });
    } catch (err: unknown) {
      agniService.stopSpeechRecognition();
      agniService.stopAudioCapture();
      setStatus("error");
      setError(
        (err as AgniError) || {
          code: "UNKNOWN",
          message: "FAILED TO INITIALIZE AUDIO",
          timestamp: Date.now(),
          retryable: true,
        }
      );
    }
  }, [processTranscript]);

  /**
   * Stop Listening Flow
   */
  const stopListening = useCallback(() => {
    agniService.stopSpeechRecognition();
    agniService.stopAudioCapture();
    agniService.stopSpeechSynthesis?.();
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (status === "listening" || status === "activating" || status === "speaking") {
      setStatus("idle");
    }
  }, [status]);

  /**
   * Open AGNI Console
   */
  const openAgni = useCallback(() => {
    setIsOpen(true);
    if (autoStartOnOpen && status === "idle") {
      startListening();
    }
  }, [autoStartOnOpen, status, startListening]);

  /**
   * Close AGNI Console and release audio
   */
  const closeAgni = useCallback(() => {
    stopListening();
    setIsOpen(false);
    setStatus("idle");
  }, [stopListening]);

  /**
   * Toggle Open/Closed
   */
  const toggleAgni = useCallback(() => {
    if (isOpen) {
      closeAgni();
    } else {
      openAgni();
    }
  }, [isOpen, closeAgni, openAgni]);

  /**
   * Toggle Mute for Voice Responses
   */
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      agniService.isTtsMuted = next;
      return next;
    });
  }, []);

  /**
   * Dismiss Active Error
   */
  const dismissError = useCallback(() => {
    setError(null);
    setStatus("idle");
  }, []);

  /**
   * Retry Microphone Capture
   */
  const retryListening = useCallback(async () => {
    dismissError();
    await startListening();
  }, [dismissError, startListening]);

  /**
   * Execute Typed Raw Action directly
   */
  const executeRawAction = useCallback(
    async (action: AgniAction): Promise<boolean> => {
      return await agniService.executeAction(action, actionHandlers);
    },
    [actionHandlers]
  );

  /**
   * Execute Structured Command directly
   */
  const executeStructuredCommand = useCallback(
    async (command: AgniStructuredCommand): Promise<boolean> => {
      return await agniService.executeStructuredCommand(command, actionHandlers);
    },
    [actionHandlers]
  );

  /**
   * Execute Tactical Demo Preset Flow
   */
  const executeDemoPreset = useCallback(
    async (preset: AgniDemoPreset) => {
      await processTranscript(preset.spokenPrompt, "demo");
    },
    [processTranscript]
  );

  /**
   * Submit Text Command directly
   */
  const submitTextCommand = useCallback(
    async (text: string) => {
      await processTranscript(text, "simulated");
    },
    [processTranscript]
  );

  return {
    status,
    isOpen,
    transcript,
    response,
    error,
    audioTelemetry,
    context,
    demoPresets: AGNI_DEMO_PRESETS,
    isSpeechRecognitionSupported,
    isMuted,
    openAgni,
    closeAgni,
    toggleAgni,
    toggleMute,
    startListening,
    stopListening,
    dismissError,
    retryListening,
    processTranscript,
    executeDemoPreset,
    submitTextCommand,
    executeStructuredCommand,
    executeRawAction,
  };
}
