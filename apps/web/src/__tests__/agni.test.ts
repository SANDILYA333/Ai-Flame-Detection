/**
 * AGNI Voice Intelligence Assistant — Phase 3 Test Suite
 * Tests state machine transitions, action contracts, context derivation,
 * audio telemetry normalization, demo verification presets, map actions,
 * layer toggles, XAI, plume hazard controls, and TTS speech synthesis.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import type {
  AgniAction,
  AgniActionHandlers,
  AgniContext,
  AgniError,
  AgniStatus,
  AgniTranscript,
} from "../services/agni/agniTypes.ts";
import {
  agniService,
  AGNI_DEMO_PRESETS,
} from "../services/agni/agniService.ts";

describe("AGNI Voice Intelligence Architecture & State Machine Suite", () => {
  it("Step 1: Validates complete AGNI state machine definitions", () => {
    const validStates: AgniStatus[] = [
      "idle",
      "activating",
      "listening",
      "processing",
      "executing",
      "speaking",
      "error",
    ];

    validStates.forEach((state) => {
      assert.ok(typeof state === "string");
    });
    assert.equal(validStates.length, 7);
  });

  it("Step 2: Validates type-safe AGNI action execution dispatcher", async () => {
    let appliedClassification = "";
    let appliedPriority = "";
    let appliedSearch = "";
    let selectedEventId = "";
    let toggledLayerId = "";
    let resetCalled = false;
    let simLabOpened = false;

    const handlers: AgniActionHandlers = {
      setClassification: (cls) => {
        appliedClassification = cls;
      },
      setPriority: (prio) => {
        appliedPriority = prio;
      },
      setSearchQuery: (q) => {
        appliedSearch = q;
      },
      selectEvent: (id) => {
        selectedEventId = id;
      },
      toggleLayer: (layer) => {
        toggledLayerId = layer;
      },
      resetFilters: () => {
        resetCalled = true;
      },
      openSimLab: () => {
        simLabOpened = true;
      },
    };

    // A. FILTER_INCIDENTS action
    const filterAction: AgniAction = {
      type: "FILTER_INCIDENTS",
      filters: {
        classification: "INDUSTRIAL",
        priority: "CRITICAL",
        searchQuery: "Jamnagar",
      },
    };

    const filterResult = await agniService.executeAction(filterAction, handlers);
    assert.equal(filterResult, true);
    assert.equal(appliedClassification, "INDUSTRIAL");
    assert.equal(appliedPriority, "CRITICAL");
    assert.equal(appliedSearch, "Jamnagar");

    // B. SELECT_INCIDENT action
    const selectAction: AgniAction = {
      type: "SELECT_INCIDENT",
      eventId: "evt_001_singrauli",
    };
    const selectResult = await agniService.executeAction(selectAction, handlers);
    assert.equal(selectResult, true);
    assert.equal(selectedEventId, "evt_001_singrauli");

    // C. TOGGLE_LAYER action
    const layerAction: AgniAction = {
      type: "TOGGLE_LAYER",
      layerId: "india-emergency-services",
    };
    const layerResult = await agniService.executeAction(layerAction, handlers);
    assert.equal(layerResult, true);
    assert.equal(toggledLayerId, "india-emergency-services");

    // D. RESET_VIEW action
    const resetAction: AgniAction = {
      type: "RESET_VIEW",
    };
    const resetResult = await agniService.executeAction(resetAction, handlers);
    assert.equal(resetResult, true);
    assert.equal(resetCalled, true);

    // E. OPEN_SIMULATION_LAB action
    const simAction: AgniAction = {
      type: "OPEN_SIMULATION_LAB",
    };
    const simResult = await agniService.executeAction(simAction, handlers);
    assert.equal(simResult, true);
    assert.equal(simLabOpened, true);
  });

  it("Step 3: Validates contextual snapshot structure (AgniContext)", () => {
    const mockContext: AgniContext = {
      selectedEventId: "evt_jamnagar_001",
      selectedEventSummary: "Petrochemical crude distillation flaring",
      lastCommand: undefined,
      lastFilters: undefined,
      activeFilters: {
        classification: "INDUSTRIAL",
        priority: "ALL",
        timeRange: "24h",
        searchQuery: "",
      },
      activeLayers: {
        "nasa-firms-viirs": true,
        "india-industrial-facilities": true,
      },
      visibleEventCount: 14,
      totalEventCount: 42,
      isLiveBackend: true,
      playbackMode: "LIVE",
      isPlaybackPlaying: false,
      currentCoordinates: {
        lat: 22.4707,
        lon: 70.0577,
      },
    };

    assert.equal(mockContext.selectedEventId, "evt_jamnagar_001");
    assert.equal(mockContext.activeFilters.classification, "INDUSTRIAL");
    assert.equal(mockContext.visibleEventCount, 14);
    assert.equal(mockContext.totalEventCount, 42);
    assert.equal(mockContext.isLiveBackend, true);
    assert.ok(mockContext.currentCoordinates);
    assert.equal(mockContext.currentCoordinates.lat, 22.4707);
  });

  it("Step 4: Gracefully handles audio capture errors in non-browser / headless environments", async () => {
    try {
      await agniService.startAudioCapture();
    } catch (err: unknown) {
      const agniErr = err as AgniError;
      assert.ok(agniErr.code, "Error code must exist");
      assert.ok(
        ["UNSUPPORTED", "DEVICE_NOT_FOUND", "PERMISSION_DENIED", "AUDIO_CAPTURE_FAILED"].includes(
          agniErr.code
        ),
        `Unexpected error code: ${agniErr.code}`
      );
      assert.ok(agniErr.message.length > 0);
    } finally {
      agniService.stopAudioCapture();
    }
  });

  it("Step 5: Validates audio telemetry normalizer produces 8 frequency bins", () => {
    const telemetry = agniService.getAudioTelemetry();
    assert.equal(typeof telemetry.amplitude, "number");
    assert.ok(telemetry.amplitude >= 0.0 && telemetry.amplitude <= 1.0);
    assert.ok(Array.isArray(telemetry.frequencies));
    assert.equal(telemetry.frequencies.length, 8);
    telemetry.frequencies.forEach((f) => {
      assert.ok(f >= 0.0 && f <= 1.0);
    });
  });

  it("Step 6: Verifies all tactical demo presets are complete and type-safe", () => {
    assert.ok(AGNI_DEMO_PRESETS.length >= 7);

    AGNI_DEMO_PRESETS.forEach((preset) => {
      assert.ok(preset.id.length > 0, "Preset ID required");
      assert.ok(preset.label.length > 0, "Preset label required");
      assert.ok(preset.spokenPrompt.length > 0, "Spoken prompt must be non-empty");
      assert.ok(preset.action.type, "Action type must be defined");
      assert.ok(preset.expectedResponse.length > 0, "Expected response must be non-empty");
    });
  });

  it("Step 7: Validates AgniTranscript schema separation (mic vs demo)", () => {
    const micTranscript: AgniTranscript = {
      id: "tr_001",
      text: "Show all high severity industrial incidents",
      timestamp: Date.now(),
      confidence: 0.94,
      source: "microphone",
      isFinal: true,
    };

    const demoTranscript: AgniTranscript = {
      id: "tr_002",
      text: "Show all industrial thermal anomalies.",
      timestamp: Date.now(),
      confidence: 1.0,
      source: "demo",
      isFinal: true,
    };

    assert.equal(micTranscript.source, "microphone");
    assert.equal(demoTranscript.source, "demo");
    assert.ok(micTranscript.confidence && micTranscript.confidence > 0.9);
  });

  it("Step 8: Phase 3 — Interprets natural language industrial command into structured response", async () => {
    const res = await agniService.interpretTranscript(
      "Show all industrial thermal anomalies."
    );

    assert.ok(res.command, "Command must exist");
    assert.ok(
      res.command.intent === "FILTER_THERMAL_EVENTS" ||
        res.command.intent === "FILTER_THERMAL_ANOMALIES"
    );
    assert.ok(
      res.command.filters.classification === "INDUSTRIAL" ||
        res.command.filters.industrial === true ||
        res.command.filters.category === "industrial"
    );
    assert.ok(res.command.confidence >= 0.80);
    assert.ok(res.message.toLowerCase().includes("industrial"));
  });


  it("Step 9: Phase 3 — Map Action & Basemap switching", async () => {
    let appliedBasemap = "";
    let appliedViewMode = "";

    const handlers: AgniActionHandlers = {
      setBasemap: (b) => {
        appliedBasemap = b;
      },
      setViewMode: (v) => {
        appliedViewMode = v;
      },
    };

    const res = await agniService.interpretTranscript("Switch to satellite view");
    assert.equal(res.command.intent, "MAP_ACTION");
    assert.equal(res.command.basemap, "satellite");

    await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(appliedBasemap, "satellite");
  });

  it("Step 10: Phase 3 — Layer Controls (Responders, FIRMS, Forests)", async () => {
    let toggledLayer = "";
    let enabledState: boolean | undefined = undefined;

    const handlers: AgniActionHandlers = {
      toggleLayer: (l, e) => {
        toggledLayer = l;
        enabledState = e;
      },
    };

    const res = await agniService.interpretTranscript("Show emergency responders");
    assert.equal(res.command.intent, "TOGGLE_LAYER");
    assert.equal(res.command.layerId, "india-emergency-services");

    await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(toggledLayer, "india-emergency-services");
  });

  it("Step 11: Phase 3 — XAI and Plume Hazard dispatchers", async () => {
    let xaiOpened = false;
    let hazardOpened = false;

    const handlers: AgniActionHandlers = {
      openXai: () => {
        xaiOpened = true;
      },
      showHazard: () => {
        hazardOpened = true;
      },
    };

    const resXai = await agniService.interpretTranscript("Explain this incident");
    assert.equal(resXai.command.intent, "OPEN_XAI");
    await agniService.executeStructuredCommand(resXai.command, handlers);
    assert.equal(xaiOpened, true);

    const resPlume = await agniService.interpretTranscript("Show the toxic plume and hazard zone");
    assert.equal(resPlume.command.intent, "SHOW_HAZARD");
    await agniService.executeStructuredCommand(resPlume.command, handlers);
    assert.equal(hazardOpened, true);
  });

  it("Step 12: Phase 3 — Multi-turn Conversational Context Merging", async () => {
    const context: AgniContext = {
      activeFilters: {
        classification: "INDUSTRIAL",
        priority: "ALL",
        timeRange: "24h",
        searchQuery: "",
      },
      lastFilters: {
        classification: "INDUSTRIAL",
        category: "industrial",
      },
      activeLayers: {},
      visibleEventCount: 10,
      totalEventCount: 30,
      isLiveBackend: true,
      playbackMode: "LIVE",
      isPlaybackPlaying: false,
    };

    const res = await agniService.interpretTranscript("Only the critical ones", context);
    assert.equal(res.command.filters.classification, "INDUSTRIAL");
    assert.equal(res.command.filters.priority, "CRITICAL");
  });

  it("Step 13: Phase 3 — Ambiguous Command Clarification", async () => {
    const res = await agniService.interpretTranscript("Show the dangerous ones");
    assert.ok(
      res.command.intent === "CLARIFICATION_REQUIRED" ||
        res.command.requiresConfirmation === true ||
        res.status === "ambiguous"
    );
    assert.ok(res.message.toLowerCase().includes("critical") || res.message.toLowerCase().includes("clarify"));
  });

  it("Step 14: Phase 5 — Multi-step Compound Command Execution", async () => {
    let appliedClass = "";
    let criterionUsed = "";
    let toggledLayer = "";

    const handlers: AgniActionHandlers = {
      setClassification: (cls) => {
        appliedClass = cls;
      },
      selectEventByCriterion: (crit) => {
        criterionUsed = crit;
      },
      toggleLayer: (l) => {
        toggledLayer = l;
      },
      showResponders: () => {
        toggledLayer = "india-emergency-services";
      },
    };

    const res = await agniService.interpretTranscript(
      "Show industrial fires in Gujarat and zoom into the most severe one and show emergency responders"
    );

    assert.ok(
      res.command.intent === "MULTI_STEP" ||
        res.command.intent === "FILTER_THERMAL_EVENTS" ||
        res.command.intent === "SHOW_RESPONDERS"
    );

    const executed = await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(executed, true);
    assert.equal(appliedClass, "INDUSTRIAL");
    assert.equal(toggledLayer, "india-emergency-services");
  });

  it("Step 15: Phase 5 — Pronoun Resolution with & without context", async () => {
    let responderToggled = false;
    const handlers: AgniActionHandlers = {
      toggleLayer: (l) => {
        if (l === "india-emergency-services") responderToggled = true;
      },
      showResponders: () => {
        responderToggled = true;
      },
    };

    // Case A: With context (incident selected)
    const contextWithEvent: AgniContext = {
      selectedEventId: "evt_gujarat_jamnagar_01",
      activeFilters: { classification: "ALL", priority: "ALL", timeRange: "24h", searchQuery: "" },
      activeLayers: {},
      visibleEventCount: 1,
      totalEventCount: 10,
      isLiveBackend: true,
      playbackMode: "LIVE",
      isPlaybackPlaying: false,
    };

    const resWithContext = await agniService.interpretTranscript("Show its responders", contextWithEvent);
    assert.ok(
      resWithContext.command.intent === "TOGGLE_LAYER" ||
        resWithContext.command.intent === "SHOW_RESPONDERS"
    );

    await agniService.executeStructuredCommand(resWithContext.command, handlers);
    assert.equal(responderToggled, true);

    // Case B: Without context (no incident selected)
    const contextWithoutEvent: AgniContext = {
      selectedEventId: undefined,
      activeFilters: { classification: "ALL", priority: "ALL", timeRange: "24h", searchQuery: "" },
      activeLayers: {},
      visibleEventCount: 10,
      totalEventCount: 10,
      isLiveBackend: true,
      playbackMode: "LIVE",
      isPlaybackPlaying: false,
    };

    const resWithoutContext = await agniService.interpretTranscript("Show its responders", contextWithoutEvent);
    assert.equal(resWithoutContext.command.intent, "CLARIFICATION_REQUIRED");
    assert.ok(resWithoutContext.message.toLowerCase().includes("select an incident first"));
  });

  it("Step 16: Phase 5 — Consequential Emergency Dispatch Preview", async () => {
    const res = await agniService.interpretTranscript("Notify the nearest fire station");
    assert.equal(res.command.intent, "DISPATCH_PREVIEW");
    assert.equal(res.command.isConsequential, true);
    assert.equal(res.command.requiresConfirmation, true);
    assert.ok(res.message.toLowerCase().includes("emergency notification workflow"));
  });

  it("Step 17: Phase 5 — Cancellation & Stop Command Handling", async () => {
    const res = await agniService.interpretTranscript("stop");
    assert.equal(res.command.intent, "CANCEL_ACTION");
    assert.ok(res.message.toLowerCase().includes("cancelled") || res.message.toLowerCase().includes("stopped"));
  });

  it("Step 18: Phase 6 — Unsupported / Conversational Command Handling", async () => {
    const res = await agniService.interpretTranscript("AGNI, make me a sandwich");
    assert.equal(res.command.intent, "UNKNOWN");
    assert.ok(res.message.toLowerCase().includes("control the thermal intelligence dashboard"));
  });

  it("Step 19: Phase 6 — Dossier and Atmospheric Hazard Execution", async () => {
    let dossierOpened = false;
    let hazardShown = false;

    const handlers: AgniActionHandlers = {
      openDossier: () => {
        dossierOpened = true;
      },
      showHazard: () => {
        hazardShown = true;
      },
    };

    const resDossier = await agniService.interpretTranscript("Open the incident dossier");
    assert.equal(resDossier.command.intent, "OPEN_DOSSIER");
    await agniService.executeStructuredCommand(resDossier.command, handlers);
    assert.equal(dossierOpened, true);

    const resPlume = await agniService.interpretTranscript("Show the plume");
    assert.equal(resPlume.command.intent, "SHOW_HAZARD");
    await agniService.executeStructuredCommand(resPlume.command, handlers);
    assert.equal(hazardShown, true);
  });

  it("Step 20: Bug Fix #2 — SpeechSynthesis TTS Lifecycle & Callbacks", () => {
    let cancelCount = 0;
    let spokenUtterance: any = null;
    let onStartCalled = false;
    let onEndCalled = false;

    // Mock global window.speechSynthesis in Node test environment
    const mockSpeechSynthesis = {
      paused: false,
      getVoices: () => [
        { name: "Google Indian English", lang: "en-IN", default: true },
        { name: "Google US English", lang: "en-US", default: false },
      ],
      cancel: () => {
        cancelCount += 1;
      },
      resume: () => {},
      speak: (utt: any) => {
        spokenUtterance = utt;
        if (utt.onstart) utt.onstart();
        if (utt.onend) utt.onend();
      },
    };

    class MockSpeechSynthesisUtterance {
      text: string;
      lang: string = "en-IN";
      voice: any = null;
      volume: number = 1.0;
      rate: number = 1.0;
      pitch: number = 1.0;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;
      onerror: ((err: any) => void) | null = null;

      constructor(text: string) {
        this.text = text;
      }
    }

    const originalWindow = (globalThis as any).window;
    const originalUtterance = (globalThis as any).SpeechSynthesisUtterance;

    (globalThis as any).window = {
      speechSynthesis: mockSpeechSynthesis,
    };
    (globalThis as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;

    try {
      const started = agniService.speakText("Showing 17 industrial thermal anomalies in Gujarat.", {
        onStart: () => {
          onStartCalled = true;
        },
        onEnd: () => {
          onEndCalled = true;
        },
      });

      assert.equal(started, true);
      assert.ok(cancelCount >= 1, "Should cancel previous speech queue");
      assert.ok(spokenUtterance, "Utterance should have been passed to speak");
      assert.equal(spokenUtterance.text, "Showing 17 industrial thermal anomalies in Gujarat.");
      assert.equal(spokenUtterance.voice?.lang, "en-IN");
      assert.equal(onStartCalled, true);
      assert.equal(onEndCalled, true);

      // Verify stopSpeechSynthesis cancels cleanly
      agniService.stopSpeechSynthesis();
      assert.ok(cancelCount >= 2);
    } finally {
      (globalThis as any).window = originalWindow;
      (globalThis as any).SpeechSynthesisUtterance = originalUtterance;
    }
  });

  it("Step 21: Bug Fix #2 — SpeechSynthesis Mute & Error Handling", () => {
    let speakCalled = false;

    const mockSpeechSynthesis = {
      paused: false,
      getVoices: () => [],
      cancel: () => {},
      resume: () => {},
      speak: () => {
        speakCalled = true;
      },
    };

    class MockSpeechSynthesisUtterance {
      text: string;
      constructor(text: string) {
        this.text = text;
      }
    }

    const originalWindow = (globalThis as any).window;
    const originalUtterance = (globalThis as any).SpeechSynthesisUtterance;

    (globalThis as any).window = {
      speechSynthesis: mockSpeechSynthesis,
    };
    (globalThis as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;

    try {
      // 1. Muted check
      agniService.isTtsMuted = true;
      const mutedResult = agniService.speakText("This should not speak.");
      assert.equal(mutedResult, false);
      assert.equal(speakCalled, false);

      // 2. Unmute and verify empty string rejection
      agniService.isTtsMuted = false;
      const emptyResult = agniService.speakText("   ");
      assert.equal(emptyResult, false);
    } finally {
      (globalThis as any).window = originalWindow;
      (globalThis as any).SpeechSynthesisUtterance = originalUtterance;
      agniService.isTtsMuted = false;
    }
  });

  it("Step 22: Preset 1 — Industrial Anomaly Filter executes through full pipeline", async () => {
    let appliedClass = "";
    const handlers: AgniActionHandlers = {
      setClassification: (cls) => { appliedClass = cls; },
      setSearchQuery: () => {},
    };

    const preset = AGNI_DEMO_PRESETS.find((p) => p.id === "filter_industrial");
    assert.ok(preset, "Industrial filter preset must exist");

    // Simulate what executeDemoPreset does: processTranscript -> interpretTranscript -> executeStructuredCommand
    const res = await agniService.interpretTranscript(preset!.spokenPrompt);
    assert.ok(
      res.command.intent === "FILTER_THERMAL_EVENTS" ||
      res.command.intent === "FILTER_THERMAL_ANOMALIES"
    );

    const executed = await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(executed, true);
    assert.equal(appliedClass, "INDUSTRIAL");
  });

  it("Step 23: Preset 2 — Multi-Step Industrial Gujarat executes with correct state mutations", async () => {
    let appliedClass = "";
    let searchApplied = "";
    let criterionUsed = "";

    const handlers: AgniActionHandlers = {
      setClassification: (cls) => { appliedClass = cls; },
      setSearchQuery: (q) => { searchApplied = q; },
      selectEventByCriterion: (crit) => { criterionUsed = crit; },
      toggleLayer: () => {},
      showResponders: () => {},
    };

    const preset = AGNI_DEMO_PRESETS.find((p) => p.id === "multi_step_gujarat_severe");
    assert.ok(preset, "Gujarat multi-step preset must exist");

    const res = await agniService.interpretTranscript(preset!.spokenPrompt);
    assert.ok(
      res.command.intent === "MULTI_STEP" || res.command.intent === "FILTER_THERMAL_EVENTS",
      `Expected MULTI_STEP or FILTER_THERMAL_EVENTS, got ${res.command.intent}`
    );

    const executed = await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(executed, true);
    assert.equal(appliedClass, "INDUSTRIAL");
  });

  it("Step 24: Preset 3 — Refinery + Responders multi-step executes correctly", async () => {
    let appliedClass = "";
    let responderToggled = false;

    const handlers: AgniActionHandlers = {
      setClassification: (cls) => { appliedClass = cls; },
      setSearchQuery: () => {},
      toggleLayer: (l) => {
        if (l === "india-emergency-services") responderToggled = true;
      },
      showResponders: () => { responderToggled = true; },
    };

    const preset = AGNI_DEMO_PRESETS.find((p) => p.id === "multi_step_refinery_responders");
    assert.ok(preset, "Refinery + responders preset must exist");

    const res = await agniService.interpretTranscript(preset!.spokenPrompt);
    const executed = await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(executed, true);
    assert.equal(appliedClass, "INDUSTRIAL");
    assert.equal(responderToggled, true);
  });

  it("Step 25: Preset 4 — Hide Forests + Focus Jamnagar multi-step executes", async () => {
    let appliedClass = "";
    let toggledLayer = "";
    let toggledEnabled: boolean | undefined;
    let searchQuery = "";

    const handlers: AgniActionHandlers = {
      setClassification: (cls) => { appliedClass = cls; },
      setSearchQuery: (q) => { searchQuery = q; },
      toggleLayer: (l, e) => { toggledLayer = l; toggledEnabled = e; },
    };

    const preset = AGNI_DEMO_PRESETS.find((p) => p.id === "multi_step_forest_jamnagar");
    assert.ok(preset, "Forest/Jamnagar preset must exist");

    const res = await agniService.interpretTranscript(preset!.spokenPrompt);
    assert.ok(
      res.command.intent === "MULTI_STEP" || res.command.intent === "FILTER_THERMAL_EVENTS",
      `Expected MULTI_STEP, got ${res.command.intent}`
    );

    const executed = await agniService.executeStructuredCommand(res.command, handlers);
    assert.equal(executed, true);
    assert.equal(appliedClass, "INDUSTRIAL");
    assert.equal(toggledLayer, "indian-forest-reserves");
    assert.equal(toggledEnabled, false);
    assert.ok(searchQuery.includes("Jamnagar"));
  });

  it("Step 26: Speech recognition callback contract validation", () => {
    // Verify startSpeechRecognition returns false in non-browser (Node) environment
    const started = agniService.startSpeechRecognition({
      onTranscript: () => {},
      onError: () => {},
      onEnd: () => {},
    });
    assert.equal(started, false, "Speech recognition should return false in non-browser env");

    // Verify stopSpeechRecognition is safe to call even without active instance
    agniService.stopSpeechRecognition();
    // No crash means pass
  });

  it("Step 27: TTS stopSpeechSynthesis is safe to call without active speech", () => {
    // Should not throw even without window.speechSynthesis
    agniService.stopSpeechSynthesis();
    // No crash means pass
  });
});
