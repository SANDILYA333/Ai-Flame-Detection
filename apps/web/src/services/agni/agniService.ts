/**
 * AGNI — AI Voice Intelligence Assistant
 * Phase 3: Service Layer, Web Speech API STT/TTS Integration & Gemini Command Dispatcher
 */

import type {
  AgniAction,
  AgniActionHandlers,
  AgniAudioTelemetry,
  AgniCommandResponse,
  AgniContext,
  AgniError,
  AgniStructuredCommand,
  IAgniService,
} from "./agniTypes.ts";

export class AgniService implements IAgniService {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyserNode: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private recognitionInstance: any = null;
  private activeAbortController: AbortController | null = null;
  private requestCounter: number = 0;
  private currentUtterance: any = null;
  private availableVoices: any[] = [];
  private voicesInitialized: boolean = false;
  private ttsResumeInterval: ReturnType<typeof setInterval> | null = null;
  public isTtsMuted: boolean = false;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.initVoices();
    }
  }

  /**
   * Populate available browser SpeechSynthesis voices
   */
  private initVoices(): void {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      this.availableVoices = window.speechSynthesis.getVoices() || [];
      if (this.availableVoices.length > 0) {
        this.voicesInitialized = true;
      }
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => {
          try {
            this.availableVoices = window.speechSynthesis.getVoices() || [];
            this.voicesInitialized = true;
          } catch {
            // Ignore voice change listener errors
          }
        };
      }
    } catch {
      // Ignore initial voice load errors in headless environments
    }
  }

  /**
   * Wait for browser voices to become available (max 2s timeout).
   * Chromium loads voices asynchronously; getVoices() returns [] on first call.
   */
  private waitForVoices(): Promise<void> {
    if (this.voicesInitialized && this.availableVoices.length > 0) {
      return Promise.resolve();
    }
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      // Try immediate load
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        this.availableVoices = voices;
        this.voicesInitialized = true;
        resolve();
        return;
      }
      // Wait for voiceschanged event with timeout
      const timeout = setTimeout(() => {
        this.voicesInitialized = true; // proceed even without voices
        resolve();
      }, 2000);
      const handler = () => {
        clearTimeout(timeout);
        try {
          this.availableVoices = window.speechSynthesis.getVoices() || [];
          this.voicesInitialized = true;
        } catch { /* ignore */ }
        resolve();
      };
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.addEventListener("voiceschanged", handler, { once: true });
      } else {
        clearTimeout(timeout);
        this.voicesInitialized = true;
        resolve();
      }
    });
  }

  /**
   * Start Chromium TTS keep-alive interval.
   * Chromium silently kills SpeechSynthesisUtterance after ~15 seconds of continuous speech.
   * Periodically calling resume() prevents this browser bug.
   */
  private startTtsKeepAlive(): void {
    this.stopTtsKeepAlive();
    this.ttsResumeInterval = setInterval(() => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        try {
          if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        } catch { /* ignore */ }
      }
    }, 5000);
  }

  /**
   * Clear Chromium TTS keep-alive interval
   */
  private stopTtsKeepAlive(): void {
    if (this.ttsResumeInterval) {
      clearInterval(this.ttsResumeInterval);
      this.ttsResumeInterval = null;
    }
  }

  /**
   * Request microphone stream and attach Web Audio API AnalyserNode
   */

  async startAudioCapture(): Promise<MediaStream> {
    if (typeof window === "undefined" || !navigator?.mediaDevices?.getUserMedia) {
      const error: AgniError = {
        code: "UNSUPPORTED",
        message: "VOICE INPUT NOT SUPPORTED IN THIS ENVIRONMENT",
        timestamp: Date.now(),
        retryable: false,
      };
      throw error;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.mediaStream = stream;

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.audioContext = new AudioCtx();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyserNode = this.audioContext.createAnalyser();
        this.analyserNode.fftSize = 64;
        this.analyserNode.smoothingTimeConstant = 0.8;
        source.connect(this.analyserNode);
        this.dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
      }

      return stream;
    } catch (err: unknown) {
      this.stopAudioCapture();

      const errorName = (err as Error)?.name || "";
      const isDenied =
        errorName === "NotAllowedError" ||
        errorName === "PermissionDeniedError" ||
        errorName === "SecurityError";
      const isNotFound = errorName === "NotFoundError" || errorName === "DevicesNotFoundError";

      const agniError: AgniError = {
        code: isDenied
          ? "PERMISSION_DENIED"
          : isNotFound
          ? "DEVICE_NOT_FOUND"
          : "AUDIO_CAPTURE_FAILED",
        message: isDenied
          ? "MICROPHONE ACCESS DENIED"
          : isNotFound
          ? "NO AUDIO INPUT DEVICE DETECTED"
          : "UNABLE TO INITIALIZE AUDIO STREAM",
        technicalDetails: (err as Error)?.message || String(err),
        timestamp: Date.now(),
        retryable: true,
      };

      throw agniError;
    }
  }

  /**
   * Stop audio capture, clean up tracks, close AudioContext
   */
  stopAudioCapture(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore track stop errors
        }
      });
      this.mediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== "closed") {
      try {
        this.audioContext.close();
      } catch {
        // Ignore audioContext close errors
      }
      this.audioContext = null;
    }

    this.analyserNode = null;
    this.dataArray = null;
  }

  /**
   * Initialize and start Web Speech API speech-to-text recognition
   */
  startSpeechRecognition(callbacks: {
    onTranscript: (text: string, isFinal: boolean) => void;
    onError?: (err: AgniError) => void;
    onEnd?: () => void;
  }): boolean {
    if (typeof window === "undefined") return false;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      return false;
    }

    try {
      this.stopSpeechRecognition();

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-IN";
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            finalTranscript += res[0].transcript;
          } else {
            interimTranscript += res[0].transcript;
          }
        }

        if (finalTranscript.trim()) {
          callbacks.onTranscript(finalTranscript.trim(), true);
        } else if (interimTranscript.trim()) {
          callbacks.onTranscript(interimTranscript.trim(), false);
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error === "no-speech") return;
        if (callbacks.onError) {
          callbacks.onError({
            code: event.error === "not-allowed" ? "PERMISSION_DENIED" : "AUDIO_CAPTURE_FAILED",
            message: `Speech recognition error: ${event.error}`,
            timestamp: Date.now(),
            retryable: true,
          });
        }
      };

      recognition.onend = () => {
        if (callbacks.onEnd) {
          callbacks.onEnd();
        }
      };

      recognition.start();
      this.recognitionInstance = recognition;
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Stop active speech recognition instance
   */
  stopSpeechRecognition(): void {
    if (this.recognitionInstance) {
      try {
        this.recognitionInstance.abort();
      } catch {
        // Ignore abort errors
      }
      this.recognitionInstance = null;
    }
  }

  /**
   * Synthesize natural verbal voice response via Web Speech Synthesis API (TTS)
   */
  speakText(
    text: string,
    callbacks?: {
      onStart?: () => void;
      onEnd?: () => void;
      onError?: (err: any) => void;
    }
  ): boolean {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return false;
    }
    if (this.isTtsMuted || !text.trim()) {
      return false;
    }

    try {
      // 1. Cancel previous utterance and stop keep-alive
      this.stopTtsKeepAlive();
      window.speechSynthesis.cancel();
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }

      // 2. Ensure voices list is populated
      if (!this.voicesInitialized || this.availableVoices.length === 0) {
        this.initVoices();
        // If still no voices, attempt synchronous re-fetch
        if (this.availableVoices.length === 0) {
          try {
            this.availableVoices = window.speechSynthesis.getVoices() || [];
            if (this.availableVoices.length > 0) this.voicesInitialized = true;
          } catch { /* ignore */ }
        }
      }

      // 3. Create utterance and retain reference in class field to prevent garbage collection
      const utterance = new SpeechSynthesisUtterance(text.trim());
      this.currentUtterance = utterance;

      // 4. Select preferred English voice (Indian / Natural / US / Default)
      if (this.availableVoices.length > 0) {
        const preferredVoice =
          this.availableVoices.find((v) => v.lang === "en-IN") ||
          this.availableVoices.find(
            (v) =>
              v.lang.startsWith("en-") &&
              (v.name.includes("Natural") ||
                v.name.includes("Google") ||
                v.name.includes("Neural"))
          ) ||
          this.availableVoices.find((v) => v.lang.startsWith("en-")) ||
          this.availableVoices[0];

        if (preferredVoice) {
          utterance.voice = preferredVoice;
          utterance.lang = preferredVoice.lang;
        } else {
          utterance.lang = "en-IN";
        }
      } else {
        utterance.lang = "en-IN";
      }

      utterance.volume = 1.0;
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        // Start Chromium keep-alive to prevent 15-second silent kill bug
        this.startTtsKeepAlive();
        if (callbacks?.onStart) {
          callbacks.onStart();
        }
      };

      utterance.onend = () => {
        this.stopTtsKeepAlive();
        this.currentUtterance = null;
        if (callbacks?.onEnd) {
          callbacks.onEnd();
        }
      };

      utterance.onerror = (event: any) => {
        this.stopTtsKeepAlive();
        if (event?.error !== "interrupted" && event?.error !== "canceled") {
          console.warn("[AGNI:TTS] Speech synthesis error:", event?.error || event);
        }
        this.currentUtterance = null;
        if (callbacks?.onError) {
          callbacks.onError(event);
        }
      };

      window.speechSynthesis.speak(utterance);

      // 5. Force resume if browser queued utterance in a paused state
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }

      return true;
    } catch (err) {
      console.warn("[AGNI:TTS] speakText exception:", err);
      this.stopTtsKeepAlive();
      this.currentUtterance = null;
      return false;
    }
  }

  /**
   * Cancel and halt any active SpeechSynthesis utterance
   */
  stopSpeechSynthesis(): void {
    this.stopTtsKeepAlive();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore cancel errors
      }
      this.currentUtterance = null;
    }
  }

  /**
   * Extract normalized amplitude & frequency telemetry for visualizers
   */
  getAudioTelemetry(): AgniAudioTelemetry {
    if (!this.analyserNode || !this.dataArray) {
      return {
        amplitude: 0,
        frequencies: [0, 0, 0, 0, 0, 0, 0, 0],
      };
    }

    (this.analyserNode as unknown as { getByteFrequencyData: (arr: Uint8Array) => void }).getByteFrequencyData(this.dataArray);

    let sum = 0;
    const bins = 8;
    const chunkSize = Math.floor(this.dataArray.length / bins);
    const frequencies: number[] = [];

    for (let i = 0; i < bins; i++) {
      let binSum = 0;
      for (let j = 0; j < chunkSize; j++) {
        binSum += this.dataArray[i * chunkSize + j];
      }
      const avg = binSum / (chunkSize * 255);
      frequencies.push(Math.min(1.0, avg));
      sum += avg;
    }

    const amplitude = Math.min(1.0, sum / bins);

    return {
      amplitude,
      frequencies,
      isClipping: amplitude > 0.95,
    };
  }

  /**
   * Send recognized transcript to backend Gemini interpreter (/api/v1/agni/interpret)
   */
  async interpretTranscript(
    transcript: string,
    context?: AgniContext
  ): Promise<AgniCommandResponse> {
    const startTime = performance.now();
    this.requestCounter += 1;
    const currentRequestId = this.requestCounter;

    // Abort previous in-flight HTTP request to prevent race conditions
    if (this.activeAbortController) {
      try {
        this.activeAbortController.abort();
      } catch {
        // Ignore abort errors
      }
    }

    const abortController = new AbortController();
    this.activeAbortController = abortController;

    try {
      const response = await fetch("http://localhost:8000/api/v1/agni/interpret", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        signal: abortController.signal,
        body: JSON.stringify({
          transcript,
          context: context
            ? {
                selectedEventId: context.selectedEventId,
                lastCommand: context.lastCommand,
                lastIntent: context.lastIntent,
                lastFilters: context.lastFilters,
                activeFilters: context.activeFilters,
                activeLayers: context.activeLayers,
                visibleEventCount: context.visibleEventCount,
                totalEventCount: context.totalEventCount,
              }
            : null,
        }),
      });

      if (currentRequestId === this.requestCounter && response.ok) {
        const data = (await response.json()) as AgniCommandResponse;
        return data;
      }
    } catch (err: unknown) {
      if ((err as Error)?.name === "AbortError") {
        return {
          command: {
            intent: "UNKNOWN",
            filters: {},
            confidence: 0.0,
            response: "Request superseded by newer operator command.",
            entities: [],
          },
          message: "Command cancelled.",
          executionLatencyMs: performance.now() - startTime,
          status: "cancelled",
        };
      }
      // Backend unavailable or network error: activate client-side deterministic fallback
    } finally {
      if (this.activeAbortController === abortController) {
        this.activeAbortController = null;
      }
    }

    // Client-side deterministic fallback interpreter
    return this.fallbackClientInterpret(transcript, startTime, context);
  }


  /**
   * Client-side semantic matcher fallback
   */
  private fallbackClientInterpret(
    transcript: string,
    startTime: number,
    context?: AgniContext
  ): AgniCommandResponse {
    const lowered = transcript.toLowerCase().trim();
    const latency = performance.now() - startTime;

    // 0. Cancellation / Stop
    if (["stop", "cancel", "halt", "abort", "quiet", "stop listening"].includes(lowered)) {
      return {
        command: {
          intent: "CANCEL_ACTION",
          filters: {},
          confidence: 0.99,
          response: "Command cancelled. Returning to idle.",
          entities: ["cancel"],
          executionTrace: ["Operation → Cancelled"],
        },
        message: "Command cancelled. Returning to idle.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 1. Consequential Emergency Dispatch Preview
    if (
      lowered.includes("notify the nearest fire station") ||
      lowered.includes("trigger emergency dispatch") ||
      lowered.includes("dispatch responder") ||
      lowered.includes("send emergency alert")
    ) {
      return {
        command: {
          intent: "DISPATCH_PREVIEW",
          filters: {},
          confidence: 0.95,
          requiresConfirmation: true,
          isConsequential: true,
          response: "This will initiate an emergency notification workflow for the selected incident. Do you want me to proceed?",
          entities: ["emergency_dispatch"],
          executionTrace: ["Action → Consequential Dispatch Preview", "State → Awaiting Confirmation"],
        },
        message: "This will initiate an emergency notification workflow for the selected incident. Do you want me to proceed?",
        executionLatencyMs: latency,
        status: "ambiguous",
      };
    }

    // 2. Reset / Clear
    const isClearPhrase =
      lowered.includes("clear") ||
      lowered.includes("reset") ||
      lowered.includes("remove all") ||
      lowered === "show all" ||
      lowered === "show everything" ||
      lowered === "show all incidents" ||
      ((lowered.includes("show all") || lowered.includes("show everything")) &&
        !lowered.includes("industr") &&
        !lowered.includes("factory") &&
        !lowered.includes("refinery") &&
        !lowered.includes("critical") &&
        !lowered.includes("high") &&
        !lowered.includes("wildfire") &&
        !lowered.includes("crop") &&
        !lowered.includes("telangana") &&
        !lowered.includes("gujarat"));

    if (isClearPhrase) {
      return {
        command: {
          intent: "CLEAR_FILTERS",
          filters: {},
          confidence: 0.98,
          response: "All filters cleared. Displaying full operational catalog.",
          entities: ["all"],
          executionTrace: ["Filters → Cleared", "Catalog → Restored Full View"],
        },
        message: "All filters cleared. Displaying full operational catalog.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 3. Ambiguity checks
    if (lowered.includes("near the city") || lowered.includes("near a city")) {
      return {
        command: {
          intent: "CLARIFICATION_REQUIRED",
          filters: {},
          confidence: 0.50,
          requiresConfirmation: true,
          response: "Which city should I use?",
          entities: ["ambiguous_city"],
        },
        message: "Which city should I use?",
        executionLatencyMs: latency,
        status: "ambiguous",
      };
    }

    if (
      lowered.includes("dangerous") ||
      lowered.includes("the bad ones") ||
      lowered.includes("the worst ones")
    ) {
      return {
        command: {
          intent: "CLARIFICATION_REQUIRED",
          filters: {},
          confidence: 0.55,
          requiresConfirmation: true,
          response: "Do you mean critical and high-severity incidents?",
          entities: ["ambiguous_severity"],
        },
        message: "Do you mean critical and high-severity incidents?",
        executionLatencyMs: latency,
        status: "ambiguous",
      };
    }

    // 4. Pronoun & Context Commands ("its responders", "its dossier", "its plume")
    const contextSelectedId = context?.selectedEventId;
    const isStrictRelativeCommand =
      lowered.includes("its responders") ||
      lowered.includes("responders near this incident") ||
      lowered.includes("responders near it") ||
      lowered.includes("responders near there");

    if (isStrictRelativeCommand && !contextSelectedId) {
      return {
        command: {
          intent: "CLARIFICATION_REQUIRED",
          filters: {},
          confidence: 0.60,
          requiresConfirmation: true,
          response: "Please select an incident first, or tell me which incident you want.",
          entities: ["missing_selected_incident"],
        },
        message: "Please select an incident first, or tell me which incident you want.",
        executionLatencyMs: latency,
        status: "ambiguous",
      };
    }

    // 5. Multi-Step Compound Commands
    // A. "Show industrial fires in Gujarat and zoom into the most severe one [and show emergency responders]"
    if (
      (lowered.includes("industr") || lowered.includes("refinery") || lowered.includes("fires")) &&
      (lowered.includes("gujarat") || lowered.includes("telangana")) &&
      (lowered.includes("zoom") || lowered.includes("severe") || lowered.includes("worst"))
    ) {
      const detectedState = lowered.includes("gujarat") ? "Gujarat" : "Telangana";
      const step1: AgniStructuredCommand = {
        intent: "FILTER_THERMAL_EVENTS",
        filters: { classification: "INDUSTRIAL", industrial: true, state: detectedState },
        confidence: 0.96,
        entities: ["industrial", detectedState],
      };
      const step2: AgniStructuredCommand = {
        intent: "SELECT_INCIDENT",
        targetCriterion: "most_severe",
        mapAction: "ZOOM_IN",
        action: "ZOOM_IN",
        filters: {},
        confidence: 0.96,
        entities: ["most_severe"],
      };
      const steps: AgniStructuredCommand[] = [step1, step2];
      const trace: string[] = [
        "Category → Industrial",
        `Region → ${detectedState}`,
        "Target → Most Severe Incident",
        "Map → Focused & Zoomed",
      ];

      if (lowered.includes("responder") || lowered.includes("emergency") || lowered.includes("station")) {
        steps.push({
          intent: "SHOW_RESPONDERS",
          layerId: "india-emergency-services",
          enabled: true,
          filters: {},
          confidence: 0.96,
          entities: ["india-emergency-services"],
        });
        trace.push("Layer → Emergency Responders Activated");
      }

      return {
        command: {
          intent: "MULTI_STEP",
          filters: { classification: "INDUSTRIAL", industrial: true, state: detectedState },
          confidence: 0.96,
          response: `Showing industrial thermal anomalies in ${detectedState}, focusing on the most severe incident${lowered.includes("responder") ? ", and showing emergency responders" : ""}.`,
          entities: ["industrial", detectedState, "most_severe"],
          steps,
          executionTrace: trace,
        },
        message: `Showing industrial thermal anomalies in ${detectedState}, focusing on the most severe incident${lowered.includes("responder") ? ", and showing emergency responders" : ""}.`,
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // B. "Show refinery fires and display the nearest emergency responders"
    if (
      (lowered.includes("refinery") || lowered.includes("petrochemical")) &&
      (lowered.includes("responder") || lowered.includes("fire station"))
    ) {
      const step1: AgniStructuredCommand = {
        intent: "FILTER_THERMAL_EVENTS",
        filters: { classification: "INDUSTRIAL", industrial: true, sector: "Refinery & Petrochemicals" },
        confidence: 0.96,
        entities: ["Refinery & Petrochemicals"],
      };
      const step2: AgniStructuredCommand = {
        intent: "SHOW_RESPONDERS",
        layerId: "india-emergency-services",
        enabled: true,
        filters: {},
        confidence: 0.96,
        entities: ["india-emergency-services"],
      };
      return {
        command: {
          intent: "MULTI_STEP",
          filters: { classification: "INDUSTRIAL", industrial: true, sector: "Refinery & Petrochemicals" },
          confidence: 0.96,
          response: "Showing refinery fires and activating nearest emergency responders overlay.",
          entities: ["Refinery & Petrochemicals", "india-emergency-services"],
          steps: [step1, step2],
          executionTrace: [
            "Sector → Refinery & Petrochemicals",
            "Layer → Emergency Responders Activated",
          ],
        },
        message: "Showing refinery fires and activating nearest emergency responders overlay.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // C. "Show industrial anomalies, hide forest reserves, and zoom to Jamnagar"
    if (lowered.includes("industr") && lowered.includes("forest") && (lowered.includes("jamnagar") || lowered.includes("zoom"))) {
      const targetCity = lowered.includes("jamnagar") ? "Jamnagar" : "Industrial Cluster";
      const step1: AgniStructuredCommand = {
        intent: "FILTER_THERMAL_EVENTS",
        filters: { classification: "INDUSTRIAL", industrial: true },
        confidence: 0.95,
        entities: ["industrial"],
      };
      const step2: AgniStructuredCommand = {
        intent: "TOGGLE_LAYER",
        layerId: "indian-forest-reserves",
        enabled: false,
        filters: {},
        confidence: 0.95,
        entities: ["indian-forest-reserves"],
      };
      const step3: AgniStructuredCommand = {
        intent: "SEARCH",
        filters: { searchQuery: targetCity },
        confidence: 0.95,
        entities: [targetCity],
      };
      return {
        command: {
          intent: "MULTI_STEP",
          filters: { classification: "INDUSTRIAL", industrial: true },
          confidence: 0.95,
          response: `Showing industrial thermal anomalies, hiding forest reserves, and focusing on ${targetCity}.`,
          entities: ["industrial", "indian-forest-reserves", targetCity],
          steps: [step1, step2, step3],
          executionTrace: [
            "Category → Industrial",
            "Layer → Hide Forest Reserves",
            `Search → ${targetCity}`,
          ],
        },
        message: `Showing industrial thermal anomalies, hiding forest reserves, and focusing on ${targetCity}.`,
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 6. Basemap & Map View Controls
    if (lowered.includes("satellite")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "SET_BASEMAP",
          action: "SET_BASEMAP",
          basemap: "satellite",
          filters: {},
          confidence: 0.96,
          response: "Satellite view enabled.",
          entities: ["satellite"],
          executionTrace: ["Basemap → Satellite Imagery"],
        },
        message: "Satellite view enabled.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("dark map") || lowered.includes("dark view")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "SET_BASEMAP",
          action: "SET_BASEMAP",
          basemap: "dark",
          filters: {},
          confidence: 0.96,
          response: "Dark cartographic basemap enabled.",
          entities: ["dark"],
          executionTrace: ["Basemap → Dark Cartography"],
        },
        message: "Dark cartographic basemap enabled.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("openstreetmap") || lowered.includes("osm") || lowered.includes("street map")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "SET_BASEMAP",
          action: "SET_BASEMAP",
          basemap: "osm",
          filters: {},
          confidence: 0.96,
          response: "OpenStreetMap basemap enabled.",
          entities: ["osm"],
          executionTrace: ["Basemap → OpenStreetMap"],
        },
        message: "OpenStreetMap basemap enabled.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("recenter") || lowered.includes("india view") || lowered.includes("reset view")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "RECENTER_INDIA",
          action: "RECENTER_INDIA",
          filters: {},
          confidence: 0.98,
          response: "Recentered map to India operational overview.",
          entities: ["recenter"],
          executionTrace: ["Map → Recentered to India Overview"],
        },
        message: "Recentered map to India operational overview.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("switch to 3d") || lowered.includes("orbital view") || lowered.includes("globe")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "SET_VIEW_MODE",
          action: "SET_VIEW_MODE",
          viewMode: "3D",
          filters: {},
          confidence: 0.98,
          response: "3D orbital globe view enabled.",
          entities: ["3D"],
          executionTrace: ["Mode → 3D Orbital Globe"],
        },
        message: "3D orbital globe view enabled.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("switch to 2d") || lowered.includes("flat map")) {
      return {
        command: {
          intent: "MAP_ACTION",
          mapAction: "SET_VIEW_MODE",
          action: "SET_VIEW_MODE",
          viewMode: "2D",
          filters: {},
          confidence: 0.98,
          response: "2D planar cartography enabled.",
          entities: ["2D"],
          executionTrace: ["Mode → 2D Planar Map"],
        },
        message: "2D planar cartography enabled.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 7. GIS Layers
    if (lowered.includes("responder") || lowered.includes("fire station") || lowered.includes("hospital") || lowered.includes("ndrf")) {
      const isEnabled = !lowered.includes("hide") && !lowered.includes("turn off");
      return {
        command: {
          intent: "TOGGLE_LAYER",
          layerId: "india-emergency-services",
          enabled: isEnabled,
          targetIncidentId: contextSelectedId,
          selectedEventId: contextSelectedId,
          filters: {},
          confidence: 0.95,
          response: `Emergency responders are now ${isEnabled ? "visible" : "hidden"}.`,
          entities: ["india-emergency-services"],
          executionTrace: ["Layer → India Emergency Services"],
        },
        message: `Emergency responders are now ${isEnabled ? "visible" : "hidden"}.`,
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("forest reserve") || (lowered.includes("forest") && lowered.includes("layer"))) {
      const isEnabled = !lowered.includes("hide") && !lowered.includes("turn off");
      return {
        command: {
          intent: "TOGGLE_LAYER",
          layerId: "indian-forest-reserves",
          enabled: isEnabled,
          filters: {},
          confidence: 0.95,
          response: `Forest reserves layer ${isEnabled ? "enabled" : "hidden"}.`,
          entities: ["indian-forest-reserves"],
          executionTrace: [`Layer → Forest Reserves (${isEnabled ? "Visible" : "Hidden"})`],
        },
        message: `Forest reserves layer ${isEnabled ? "enabled" : "hidden"}.`,
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("live firms") || lowered.includes("live nasa") || lowered.includes("satellite hotspots") || lowered.includes("live satellite")) {
      return {
        command: {
          intent: "TOGGLE_LAYER",
          layerId: "nasa-firms-live-api",
          enabled: !lowered.includes("hide") && !lowered.includes("turn off"),
          filters: {},
          confidence: 0.96,
          response: "Live NASA FIRMS satellite feed activated.",
          entities: ["nasa-firms-live-api"],
          executionTrace: ["Layer → NASA FIRMS Real-time Stream"],
        },
        message: "Live NASA FIRMS satellite feed activated.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 8. Intelligence / XAI & Hazard Plumes
    if (lowered.includes("explain") || lowered.includes("xai") || lowered.includes("evidence") || lowered.includes("why this was classified")) {
      return {
        command: {
          intent: "OPEN_XAI",
          selectedEventId: contextSelectedId,
          incidentId: contextSelectedId,
          filters: {},
          confidence: 0.96,
          response: "Opening Explainable AI analysis panel.",
          entities: ["xai"],
          executionTrace: ["XAI → Attribution Panel Opened"],
        },
        message: "Opening Explainable AI analysis panel.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("plume") || lowered.includes("hazard zone") || lowered.includes("toxic") || lowered.includes("dispersion")) {
      return {
        command: {
          intent: "SHOW_HAZARD",
          selectedEventId: contextSelectedId,
          incidentId: contextSelectedId,
          filters: {},
          confidence: 0.96,
          response: "Displaying Gaussian atmospheric plume dispersion and hazard corridor.",
          entities: ["plume"],
          executionTrace: ["Physics → Atmospheric Dispersion Plume"],
        },
        message: "Displaying Gaussian atmospheric plume dispersion and hazard corridor.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }
    if (lowered.includes("dossier") || lowered.includes("incident report") || lowered.includes("briefing")) {
      return {
        command: {
          intent: "OPEN_DOSSIER",
          selectedEventId: contextSelectedId,
          incidentId: contextSelectedId,
          filters: {},
          confidence: 0.96,
          response: "Opening tactical incident briefing dossier.",
          entities: ["dossier"],
          executionTrace: ["Briefing → Tactical Dossier Modal"],
        },
        message: "Opening tactical incident briefing dossier.",
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // 9. Time Range
    let detectedTime: string | null = null;
    if (lowered.includes("24 hour") || lowered.includes("today") || lowered.includes("24h")) {
      detectedTime = "24h";
    } else if (lowered.includes("7 day") || lowered.includes("week") || lowered.includes("7d")) {
      detectedTime = "7d";
    } else if (lowered.includes("1 hour") || lowered.includes("1h")) {
      detectedTime = "1h";
    } else if (lowered.includes("6 hour") || lowered.includes("6h")) {
      detectedTime = "6h";
    }

    // 10. Industrial / Category / Severity / State
    let isIndustrial = Boolean(
      lowered.includes("industr") ||
      lowered.includes("factory") ||
      lowered.includes("refinery") ||
      lowered.includes("steel") ||
      lowered.includes("petrochemical")
    );

    let detectedCategory: string | null = null;
    if (lowered.includes("wildfire") || (lowered.includes("forest") && !lowered.includes("layer"))) {
      detectedCategory = "wildfire";
    } else if (lowered.includes("crop") || lowered.includes("stubble")) {
      detectedCategory = "crop";
    } else if (lowered.includes("routine") || lowered.includes("flare")) {
      detectedCategory = "routine";
    } else if (lowered.includes("coal")) {
      detectedCategory = "coal";
    } else if (isIndustrial) {
      detectedCategory = "industrial";
    }

    let detectedPriority: string | null = null;
    if (lowered.includes("critical") || lowered.includes("urgent")) {
      detectedPriority = "CRITICAL";
    } else if (lowered.includes("high")) {
      detectedPriority = "HIGH";
    } else if (lowered.includes("medium")) {
      detectedPriority = "MEDIUM";
    } else if (lowered.includes("low")) {
      detectedPriority = "LOW";
    }

    let detectedState: string | null = null;
    const states = [
      "Telangana", "Andhra Pradesh", "Gujarat", "Maharashtra", "Odisha",
      "Jharkhand", "Chhattisgarh", "Karnataka", "Tamil Nadu", "Rajasthan",
      "Madhya Pradesh", "West Bengal", "Punjab", "Haryana", "Assam"
    ];
    for (const s of states) {
      if (lowered.includes(s.toLowerCase())) {
        detectedState = s;
        break;
      }
    }

    // Conversational context merging
    if (!isIndustrial && !detectedCategory && context?.lastFilters) {
      if (context.lastFilters.classification === "INDUSTRIAL" || context.lastFilters.category === "industrial") {
        isIndustrial = true;
        detectedCategory = "industrial";
      }
    }
    if (!detectedState && context?.lastFilters?.state) {
      detectedState = context.lastFilters.state;
    }

    if (isIndustrial || detectedCategory || detectedPriority || detectedState || detectedTime) {
      const classification = isIndustrial ? "INDUSTRIAL" : (detectedCategory === "wildfire" || detectedCategory === "crop" ? "NON_INDUSTRIAL" : null);
      
      const parts: string[] = [];
      const traceBadges: string[] = [];
      if (detectedTime) {
        parts.push(detectedTime);
        traceBadges.push(`Time → ${detectedTime}`);
      }
      if (detectedPriority) {
        parts.push(`${detectedPriority.toLowerCase()} severity`);
        traceBadges.push(`Severity → ${detectedPriority}`);
      }
      if (isIndustrial || detectedCategory === "industrial") {
        parts.push("industrial thermal anomalies");
        traceBadges.push("Category → Industrial");
      } else if (detectedCategory) {
        parts.push(`${detectedCategory} thermal anomalies`);
        traceBadges.push(`Category → ${detectedCategory.charAt(0).toUpperCase() + detectedCategory.slice(1)}`);
      } else {
        parts.push("thermal anomalies");
      }
      if (detectedState) {
        parts.push(`in ${detectedState}`);
        traceBadges.push(`Region → ${detectedState}`);
      }

      const msg = `Showing ${parts.join(" ")}.`;

      return {
        command: {
          intent: "FILTER_THERMAL_EVENTS",
          filters: {
            classification,
            priority: detectedPriority,
            severity: detectedPriority ? (detectedPriority.toLowerCase() as any) : null,
            timeRange: detectedTime,
            state: detectedState,
            category: detectedCategory,
            industrial: isIndustrial || undefined,
          },
          confidence: 0.95,
          response: msg,
          entities: [classification, detectedPriority, detectedCategory, detectedState, detectedTime].filter(Boolean) as string[],
          executionTrace: traceBadges,
        },
        message: msg,
        executionLatencyMs: latency,
        status: "fallback",
      };
    }

    // Unsupported / non-operational queries
    const isConversational =
      lowered.includes("sandwich") ||
      lowered.includes("joke") ||
      lowered.includes("who are you") ||
      lowered.includes("what can you do") ||
      lowered.includes("help") ||
      lowered.startsWith("make me") ||
      lowered.startsWith("play music");

    if (isConversational) {
      const guidance = "I can help control the thermal intelligence dashboard. Try asking me to show incidents, change filters, focus the map, or display responders.";
      return {
        command: {
          intent: "UNKNOWN",
          filters: {},
          confidence: 0.30,
          response: guidance,
          entities: [],
          executionTrace: ["Status → Unsupported Operational Query"],
        },
        message: guidance,
        executionLatencyMs: latency,
        status: "unsupported",
      };
    }

    return {
      command: {
        intent: "SEARCH",
        filters: { searchQuery: transcript },
        confidence: 0.85,
        response: `Searching incidents matching "${transcript}".`,
        entities: [transcript],
        executionTrace: [`Search → ${transcript}`],
      },
      message: `Searching incidents matching "${transcript}".`,
      executionLatencyMs: latency,
      status: "fallback",
    };
  }

  /**
   * Execute validated structured command produced by Gemini against application state handlers
   */
  async executeStructuredCommand(
    command: AgniStructuredCommand,
    handlers: AgniActionHandlers
  ): Promise<boolean> {
    if (command.confidence < 0.80 || command.requiresConfirmation || command.intent === "CLARIFICATION_REQUIRED") {
      return false;
    }

    try {
      // 1. Sequential Multi-Step Command Execution
      if (command.intent === "MULTI_STEP" || (command.steps && command.steps.length > 0)) {
        if (command.steps && command.steps.length > 0) {
          for (const step of command.steps) {
            await this.executeStructuredCommand(step, handlers);
          }
          return true;
        }
      }

      switch (command.intent) {
        case "CANCEL_ACTION": {
          return true;
        }

        case "DISPATCH_PREVIEW": {
          if (handlers.showResponders) {
            handlers.showResponders();
            return true;
          }
          return true;
        }

        case "CLEAR_FILTERS": {
          if (handlers.resetFilters) {
            handlers.resetFilters();
            return true;
          }
          return false;
        }

        case "OPEN_SIMULATION_LAB": {
          if (handlers.openSimLab) {
            handlers.openSimLab();
            return true;
          }
          return false;
        }

        case "OPEN_XAI": {
          if (handlers.openXai) {
            handlers.openXai();
            return true;
          }
          return false;
        }

        case "SHOW_HAZARD": {
          if (handlers.showHazard) {
            handlers.showHazard();
            return true;
          }
          return false;
        }

        case "OPEN_DOSSIER": {
          if (handlers.openDossier) {
            handlers.openDossier();
            return true;
          }
          return false;
        }

        case "SHOW_RESPONDERS": {
          if (handlers.showResponders) {
            handlers.showResponders();
            return true;
          }
          if (handlers.toggleLayer) {
            handlers.toggleLayer("india-emergency-services", true);
            return true;
          }
          return false;
        }

        case "MAP_ACTION": {
          if (command.mapAction === "RECENTER_INDIA" || command.action === "RECENTER_INDIA") {
            if (handlers.centerMap) {
              handlers.centerMap();
              return true;
            }
          }
          if (command.viewMode && handlers.setViewMode) {
            handlers.setViewMode(command.viewMode as "2D" | "3D");
            return true;
          }
          if (command.basemap && handlers.setBasemap) {
            handlers.setBasemap(command.basemap);
            return true;
          }
          return true;
        }

        case "SELECT_INCIDENT": {
          const targetId = command.incidentId || command.selectedEventId;
          if (targetId && handlers.selectEvent) {
            handlers.selectEvent(targetId);
            return true;
          }
          if (command.targetCriterion && handlers.selectEventByCriterion) {
            handlers.selectEventByCriterion(command.targetCriterion);
            return true;
          }
          return false;
        }

        case "SHOW_LAYER":
        case "HIDE_LAYER":
        case "TOGGLE_LAYER": {
          if (command.layerId && handlers.toggleLayer) {
            handlers.toggleLayer(command.layerId, command.enabled ?? undefined);
            return true;
          }
          return false;
        }

        case "SEARCH":
        case "SEARCH_INCIDENTS": {
          if (command.filters.searchQuery !== undefined && handlers.setSearchQuery) {
            handlers.setSearchQuery(command.filters.searchQuery || "");
            return true;
          }
          return false;
        }

        case "FILTER_THERMAL_EVENTS":
        case "FILTER_THERMAL_ANOMALIES":
        case "FILTER_SEVERITY":
        case "FILTER_CATEGORY":
        case "FILTER_STATE":
        case "FILTER_SECTOR": {
          const f = command.filters;
          if (f.classification && handlers.setClassification) {
            handlers.setClassification(f.classification);
          } else if (f.industrial && handlers.setClassification) {
            handlers.setClassification("INDUSTRIAL");
          } else if (f.category === "wildfire" || f.category === "crop") {
            if (handlers.setClassification) {
              handlers.setClassification("NON_INDUSTRIAL");
            }
          }

          if ((f.priority || f.severity) && handlers.setPriority) {
            const prio = (f.priority || f.severity || "").toUpperCase();
            handlers.setPriority(prio);
          }

          if (f.timeRange && handlers.setTimeRange) {
            handlers.setTimeRange(f.timeRange.toUpperCase());
          }

          if (f.searchQuery !== undefined && handlers.setSearchQuery) {
            handlers.setSearchQuery(f.searchQuery || "");
          } else if (f.state && handlers.setSearchQuery) {
            handlers.setSearchQuery(f.state);
          } else if (f.sector && handlers.setSearchQuery) {
            handlers.setSearchQuery(f.sector);
          }

          if (command.targetCriterion && handlers.selectEventByCriterion) {
            handlers.selectEventByCriterion(command.targetCriterion);
          }
          return true;
        }

        case "MULTI_STEP": {
          if (command.steps && command.steps.length > 0) {
            for (const step of command.steps) {
              await this.executeStructuredCommand(step, handlers);
            }
            return true;
          }
          return false;
        }

        default:
          return false;
      }
    } catch {
      return false;
    }
  }

  /**
   * Legacy typed action dispatcher (Phase 1 compatibility)
   */
  async executeAction(
    action: AgniAction,
    handlers: AgniActionHandlers
  ): Promise<boolean> {
    try {
      switch (action.type) {
        case "FILTER_INCIDENTS": {
          if (action.filters.classification && handlers.setClassification) {
            handlers.setClassification(action.filters.classification);
          }
          if (action.filters.priority && handlers.setPriority) {
            handlers.setPriority(action.filters.priority);
          }
          if (action.filters.timeRange && handlers.setTimeRange) {
            handlers.setTimeRange(action.filters.timeRange.toUpperCase());
          }
          if (action.filters.searchQuery !== undefined && handlers.setSearchQuery) {
            handlers.setSearchQuery(action.filters.searchQuery);
          } else if (action.filters.state && handlers.setSearchQuery) {
            handlers.setSearchQuery(action.filters.state);
          }
          return true;
        }

        case "SELECT_INCIDENT": {
          if (handlers.selectEvent && action.eventId) {
            handlers.selectEvent(action.eventId);
            return true;
          }
          return false;
        }

        case "SHOW_LAYER": {
          if (handlers.toggleLayer && action.layerId) {
            handlers.toggleLayer(action.layerId, true);
            return true;
          }
          return false;
        }

        case "HIDE_LAYER": {
          if (handlers.toggleLayer && action.layerId) {
            handlers.toggleLayer(action.layerId, false);
            return true;
          }
          return false;
        }

        case "TOGGLE_LAYER": {
          if (handlers.toggleLayer && action.layerId) {
            handlers.toggleLayer(action.layerId, action.enabled);
            return true;
          }
          return false;
        }

        case "MAP_ACTION": {
          if (action.action === "RECENTER_INDIA" && handlers.centerMap) {
            handlers.centerMap();
            return true;
          }
          if (action.viewMode && handlers.setViewMode) {
            handlers.setViewMode(action.viewMode);
            return true;
          }
          if (action.basemap && handlers.setBasemap) {
            handlers.setBasemap(action.basemap);
            return true;
          }
          return true;
        }

        case "SEARCH": {
          if (handlers.setSearchQuery) {
            handlers.setSearchQuery(action.query);
            return true;
          }
          return false;
        }

        case "RESET_VIEW": {
          if (handlers.resetFilters) {
            handlers.resetFilters();
            return true;
          }
          return false;
        }

        case "OPEN_XAI": {
          if (handlers.openXai) {
            handlers.openXai();
            return true;
          }
          return false;
        }

        case "SHOW_RESPONDERS": {
          if (handlers.showResponders) {
            handlers.showResponders();
            return true;
          }
          return false;
        }

        case "SHOW_HAZARD": {
          if (handlers.showHazard) {
            handlers.showHazard();
            return true;
          }
          return false;
        }

        case "OPEN_DOSSIER": {
          if (handlers.openDossier) {
            handlers.openDossier();
            return true;
          }
          return false;
        }

        case "OPEN_SIMULATION_LAB": {
          if (handlers.openSimLab) {
            handlers.openSimLab();
            return true;
          }
          return false;
        }

        default:
          return false;
      }
    } catch {
      return false;
    }
  }
}

export const agniService = new AgniService();

export interface AgniDemoPreset {
  id: string;
  label: string;
  spokenPrompt: string;
  action: AgniAction;
  expectedResponse: string;
}

export const AGNI_DEMO_PRESETS: AgniDemoPreset[] = [
  {
    id: "filter_industrial",
    label: "1. Industrial Anomaly Filter",
    spokenPrompt: "Show all industrial thermal anomalies.",
    action: {
      type: "FILTER_INCIDENTS",
      filters: { classification: "INDUSTRIAL", searchQuery: "" },
    },
    expectedResponse: "Showing industrial thermal anomalies.",
  },
  {
    id: "multi_step_gujarat_severe",
    label: "2. [Multi-Step] Industrial in Gujarat + Zoom to Severe",
    spokenPrompt: "Show industrial fires in Gujarat and zoom into the most severe one.",
    action: {
      type: "FILTER_INCIDENTS",
      filters: { classification: "INDUSTRIAL", searchQuery: "Gujarat" },
    },
    expectedResponse: "Showing industrial thermal anomalies in Gujarat and focusing on the most severe incident.",
  },
  {
    id: "multi_step_refinery_responders",
    label: "3. [Multi-Step] Refinery Fires + Nearest Responders",
    spokenPrompt: "Show refinery fires and display the nearest emergency responders.",
    action: {
      type: "FILTER_INCIDENTS",
      filters: { classification: "INDUSTRIAL", sector: "Refinery & Petrochemicals" },
    },
    expectedResponse: "Showing refinery fires and activating nearest emergency responders overlay.",
  },
  {
    id: "multi_step_forest_jamnagar",
    label: "4. [Multi-Step] Hide Forests + Focus Jamnagar",
    spokenPrompt: "Show industrial anomalies, hide forest reserves, and zoom to Jamnagar.",
    action: {
      type: "FILTER_INCIDENTS",
      filters: { classification: "INDUSTRIAL", searchQuery: "Jamnagar" },
    },
    expectedResponse: "Showing industrial thermal anomalies, hiding forest reserves, and focusing on Jamnagar.",
  },
  {
    id: "context_pronoun_responders",
    label: "5. [Context] Responders Near Selected Incident",
    spokenPrompt: "Show its emergency responders.",
    action: {
      type: "SHOW_RESPONDERS",
    },
    expectedResponse: "Displaying emergency responders nearest to incident.",
  },
  {
    id: "consequential_dispatch_preview",
    label: "6. [Consequential] Notify Nearest Fire Station",
    spokenPrompt: "Notify the nearest fire station.",
    action: {
      type: "SHOW_RESPONDERS",
    },
    expectedResponse: "This will initiate an emergency notification workflow for the selected incident. Do you want me to proceed?",
  },
  {
    id: "map_satellite",
    label: "7. Satellite View Basemap",
    spokenPrompt: "Switch to satellite view.",
    action: {
      type: "MAP_ACTION",
      action: "SET_BASEMAP",
      basemap: "satellite",
    },
    expectedResponse: "Satellite view enabled.",
  },
  {
    id: "open_xai",
    label: "8. Intelligence: Explain AI Evidence",
    spokenPrompt: "Explain this incident and show AI evidence.",
    action: {
      type: "OPEN_XAI",
    },
    expectedResponse: "Opening Explainable AI evidence card.",
  },
  {
    id: "show_plume",
    label: "9. Hazard: Toxic Plume Dispersion",
    spokenPrompt: "Show the toxic plume and hazard zone.",
    action: {
      type: "SHOW_HAZARD",
    },
    expectedResponse: "Displaying Gaussian atmospheric plume dispersion and hazard corridor.",
  },
  {
    id: "open_dossier",
    label: "10. Briefing: Open Tactical Dossier",
    spokenPrompt: "Open the tactical dossier.",
    action: {
      type: "OPEN_DOSSIER",
    },
    expectedResponse: "Opening tactical incident briefing dossier.",
  },
  {
    id: "reset_filters",
    label: "11. Reset: Full Tactical Catalog",
    spokenPrompt: "Reset all filters.",
    action: {
      type: "RESET_VIEW",
    },
    expectedResponse: "All filters cleared. Displaying full operational catalog.",
  },
  {
    id: "command_stop",
    label: "12. Control: Stop / Cancel",
    spokenPrompt: "Stop",
    action: {
      type: "RESET_VIEW",
    },
    expectedResponse: "Command cancelled. Returning to idle.",
  },
];

