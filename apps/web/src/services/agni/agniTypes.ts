/**
 * AGNI — AI Voice Intelligence Assistant
 * Phase 3: Domain Types, Gemini Structured Command Contracts & Action Mappings
 */

export type AgniStatus =
  | "idle"
  | "activating"
  | "listening"
  | "processing"
  | "executing"
  | "speaking"
  | "error";

export type AgniSource = "microphone" | "demo" | "simulated";

export type AgniIntent =
  | "FILTER_THERMAL_EVENTS"
  | "FILTER_THERMAL_ANOMALIES"
  | "FILTER_SEVERITY"
  | "FILTER_CATEGORY"
  | "FILTER_STATE"
  | "FILTER_SECTOR"
  | "SEARCH"
  | "SEARCH_INCIDENTS"
  | "SELECT_INCIDENT"
  | "MAP_ACTION"
  | "TOGGLE_LAYER"
  | "SHOW_LAYER"
  | "HIDE_LAYER"
  | "OPEN_XAI"
  | "SHOW_RESPONDERS"
  | "SHOW_HAZARD"
  | "OPEN_DOSSIER"
  | "CLEAR_FILTERS"
  | "OPEN_SIMULATION_LAB"
  | "MULTI_STEP"
  | "DISPATCH_PREVIEW"
  | "CONFIRM_ACTION"
  | "CANCEL_ACTION"
  | "CLARIFICATION_REQUIRED"
  | "UNKNOWN";


export interface AgniFilters {
  classification?: "ALL" | "INDUSTRIAL" | "NON_INDUSTRIAL" | "UNKNOWN" | "REVIEW_REQUIRED" | string | null;
  priority?: "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "REVIEW_REQUIRED" | string | null;
  severity?: "critical" | "high" | "medium" | "low" | "review_required" | string | null;
  timeRange?: "1h" | "6h" | "24h" | "48h" | "7d" | "All" | "1H" | "6H" | "24H" | "48H" | "7D" | "ALL" | string | null;
  searchQuery?: string | null;
  state?: string | null;
  sector?: string | null;
  category?: "accidental" | "routine" | "wildfire" | "crop" | "coal" | "glint" | "industrial" | string | null;
  industrial?: boolean | null;
}

export interface AgniStructuredCommand {
  intent: AgniIntent;
  filters: AgniFilters;
  selectedEventId?: string | null;
  incidentId?: string | null;
  targetIncidentId?: string | null;
  targetCriterion?: "most_severe" | "highest_frp" | "nearest" | "first" | string | null;
  layerId?: string | null;
  enabled?: boolean | null;
  basemap?: "satellite" | "dark" | "osm" | string | null;
  mapAction?: "RECENTER_INDIA" | "FIT_RESULTS" | "SET_BASEMAP" | "SET_VIEW_MODE" | "ZOOM_IN" | "ZOOM_OUT" | string | null;
  action?: string | null;
  viewMode?: "2D" | "3D" | string | null;
  confidence: number;
  requiresConfirmation?: boolean;
  isConsequential?: boolean;
  response?: string | null;
  entities: string[];
  steps?: AgniStructuredCommand[];
  executionTrace?: string[];
}

export interface AgniTranscript {
  id: string;
  text: string;
  timestamp: number;
  confidence?: number;
  source: AgniSource;
  isFinal?: boolean;
}

export interface AgniCommandResponse {
  command: AgniStructuredCommand;
  message: string;
  executionLatencyMs: number;
  status: "interpreted" | "ambiguous" | "unsupported" | "fallback" | "error" | string;
}

export interface AgniResponse {
  id: string;
  text: string;
  timestamp: number;
  actionTaken?: string;
  intent?: AgniIntent;
  confidence?: number;
  status: "success" | "warning" | "error" | "info";
  executionLatencyMs?: number;
  executionTrace?: string[];
  isConsequential?: boolean;
  requiresConfirmation?: boolean;
  matchedCount?: number;
  command?: AgniStructuredCommand;
}

export type AgniErrorCode =
  | "PERMISSION_DENIED"
  | "UNSUPPORTED"
  | "DEVICE_NOT_FOUND"
  | "AUDIO_CAPTURE_FAILED"
  | "NETWORK_ERROR"
  | "TIMEOUT"
  | "UNKNOWN";

export interface AgniError {
  code: AgniErrorCode;
  message: string;
  technicalDetails?: string;
  timestamp: number;
  retryable: boolean;
}

/**
 * Type-safe action foundation for AGNI tool executions
 */
export type AgniAction =
  | {
      type: "FILTER_INCIDENTS";
      filters: {
        classification?: "ALL" | "INDUSTRIAL" | "NON_INDUSTRIAL" | "UNKNOWN" | "REVIEW_REQUIRED" | string;
        priority?: "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "REVIEW_REQUIRED" | string;
        severity?: string;
        timeRange?: "1h" | "6h" | "24h" | "48h" | "7d" | "All" | string;
        searchQuery?: string;
        state?: string;
        sector?: string;
        category?: string;
      };
    }
  | {
      type: "SELECT_INCIDENT";
      eventId: string;
    }
  | {
      type: "SHOW_LAYER";
      layerId: string;
    }
  | {
      type: "HIDE_LAYER";
      layerId: string;
    }
  | {
      type: "TOGGLE_LAYER";
      layerId: string;
      enabled?: boolean;
    }
  | {
      type: "MAP_ACTION";
      action: "RECENTER_INDIA" | "SET_BASEMAP" | "SET_VIEW_MODE" | string;
      basemap?: string;
      viewMode?: "2D" | "3D";
    }
  | {
      type: "SEARCH";
      query: string;
    }
  | {
      type: "RESET_VIEW";
    }
  | {
      type: "OPEN_XAI";
    }
  | {
      type: "SHOW_RESPONDERS";
    }
  | {
      type: "SHOW_HAZARD";
    }
  | {
      type: "OPEN_DOSSIER";
    }
  | {
      type: "OPEN_SIMULATION_LAB";
    };


/**
 * Comprehensive application context snapshot passed to AGNI
 */
export interface AgniContext {
  selectedEventId?: string;
  selectedEventSummary?: string;
  lastCommand?: AgniStructuredCommand;
  lastIntent?: AgniIntent;
  lastFilters?: AgniFilters;
  activeFilters: {
    classification: string;
    priority: string;
    timeRange: string;
    searchQuery: string;
    state?: string;
    sector?: string;
    category?: string;
  };
  activeLayers: Record<string, boolean>;
  visibleEventCount: number;
  totalEventCount: number;
  isLiveBackend: boolean;
  playbackMode: string;
  isPlaybackPlaying: boolean;
  currentCoordinates?: {
    lat: number;
    lon: number;
  };
}

/**
 * Audio visualizer telemetry
 */
export interface AgniAudioTelemetry {
  amplitude: number; // 0.0 to 1.0
  frequencies: number[]; // Normalized frequency bins
  isClipping?: boolean;
}

export interface AgniActionHandlers {
  setClassification?: (cls: string) => void;
  setPriority?: (prio: string) => void;
  setTimeRange?: (range: string) => void;
  setSearchQuery?: (query: string) => void;
  selectEvent?: (eventId: string) => void;
  selectEventByCriterion?: (criterion: string) => void;
  toggleLayer?: (layerId: string, enabled?: boolean) => void;
  setBasemap?: (basemap: string) => void;
  setViewMode?: (mode: "2D" | "3D") => void;
  centerMap?: () => void;
  openXai?: () => void;
  showResponders?: () => void;
  showHazard?: () => void;
  openDossier?: () => void;
  resetFilters?: () => void;
  openSimLab?: () => void;
}


export interface IAgniService {
  startAudioCapture(): Promise<MediaStream>;
  stopAudioCapture(): void;
  startSpeechRecognition(callbacks: {
    onTranscript: (text: string, isFinal: boolean) => void;
    onError?: (err: AgniError) => void;
    onEnd?: () => void;
  }): boolean;
  stopSpeechRecognition(): void;
  speakText(
    text: string,
    callbacks?: {
      onStart?: () => void;
      onEnd?: () => void;
      onError?: (err: any) => void;
    }
  ): boolean;
  stopSpeechSynthesis?(): void;
  getAudioTelemetry(): AgniAudioTelemetry;
  interpretTranscript(transcript: string, context?: AgniContext): Promise<AgniCommandResponse>;
  executeStructuredCommand(command: AgniStructuredCommand, handlers: AgniActionHandlers): Promise<boolean>;
  executeAction(action: AgniAction, handlers: AgniActionHandlers): Promise<boolean>;
}
