"use client";

import React, {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef,
} from "react";
import { useEvents } from "@/hooks/useEvents";
import { backendEventToThermalEvent, ThermalEvent } from "@/types/event";
import { DEMO_THERMAL_EVENTS } from "@/features/events/mock/demo-events";
import { INITIAL_LAYERS } from "@/config/ui";
import {
  calculateWindowRange,
  deriveTimeWindowQuery,
  filterEventsByTemporalState,
} from "@/lib/playback/temporal";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import type { EventsQueryParams } from "@/types/event";
import type {
  PlaybackMode,
  PlaybackRange,
  PlaybackSpeed,
  TimeWindow,
} from "@/types/playback";

export interface EventStats {
  total: number;
  industrial: number;
  nonIndustrial: number;
  unknown: number;
  reviewRequired: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  maxFrp: number;
}

export interface EventContextType {
  // Canonical Events
  rawEvents: ThermalEvent[];
  filteredEvents: ThermalEvent[];

  // Spatial & Classification Filters
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedClassification: string;
  setSelectedClassification: (classification: string) => void;
  selectedPriority: string;
  setSelectedPriority: (priority: string) => void;
  selectedEvent: ThermalEvent | null;
  setSelectedEvent: (event: ThermalEvent | null) => void;
  isDetailOpen: boolean;
  setIsDetailOpen: (isOpen: boolean) => void;
  isDossierOpen: boolean;
  setIsDossierOpen: (isOpen: boolean) => void;
  isResponseCenterOpen: boolean;
  setIsResponseCenterOpen: (isOpen: boolean) => void;
  activeLayers: Record<string, boolean>;
  toggleLayer: (layerId: string) => void;
  timeRange: string;
  setTimeRange: (range: string) => void;

  // Temporal Playback State & Controls
  playbackMode: PlaybackMode;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  playbackTime: number;
  playbackRange: PlaybackRange;
  playbackProgress: number; // 0.0 to 1.0
  setPlaybackMode: (mode: PlaybackMode) => void;
  setPlaybackTime: (timeMs: number) => void;
  setPlaybackProgress: (progress: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
  togglePlayPause: () => void;
  stepForward: (fraction?: number) => void;
  stepBackward: (fraction?: number) => void;
  resetToLive: () => void;
  startPlayback: () => void;

  // Aggregate Metrics & Ingestion
  stats: EventStats;
  isLiveBackend: boolean;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  refetch: () => Promise<void>;
  resetFilters: () => void;
}

const EventContext = createContext<EventContextType | undefined>(undefined);

export function EventProvider({ children }: { children: React.ReactNode }) {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedClassification, setSelectedClassification] = useState<string>("ALL");
  const [selectedPriority, setSelectedPriority] = useState<string>("ALL");
  const [selectedEvent, setSelectedEvent] = useState<ThermalEvent | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(true);
  const [isDossierOpen, setIsDossierOpen] = useState<boolean>(false);
  const [isResponseCenterOpen, setIsResponseCenterOpen] = useState<boolean>(false);
  const [timeRange, setTimeRangeState] = useState<string>("ALL");


  // Temporal Playback Engine State
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>("LIVE");
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<PlaybackSpeed>(1);
  const [customPlaybackTime, setCustomPlaybackTime] = useState<number | null>(null);

  // Initialize active layers map from INITIAL_LAYERS
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    INITIAL_LAYERS.forEach((layer) => {
      initial[layer.id] = layer.enabled;
    });
    return initial;
  });

  const toggleLayer = useCallback((layerId: string) => {
    setActiveLayers((prev) => ({
      ...prev,
      [layerId]: !prev[layerId],
    }));
  }, []);

  // Derive temporal API query parameters from selected time window
  const eventQueryParams = useMemo<EventsQueryParams>(() => {
    const query = deriveTimeWindowQuery(timeRange);
    return {
      start_time: query.start_time,
      end_time: query.end_time,
      limit: 100,
    };
  }, [timeRange]);

  // Fetch live canonical thermal events from FastAPI backend matching active time window
  const {
    events: backendEvents,
    isLoading,
    isFetching,
    isError,
    refetch: rawRefetch,
  } = useEvents(eventQueryParams);

  // Map backend events to ThermalEvent and combine with comprehensive multi-source catalog
  const rawEvents = useMemo(() => {
    const eventMap = new Map<string, ThermalEvent>();

    // 1. Ingest all multi-source global events first
    DEMO_THERMAL_EVENTS.forEach((e) => {
      eventMap.set(e.event_id, e);
    });

    // 2. Ingest live backend events from FastAPI / NASA FIRMS pipeline
    if (backendEvents && backendEvents.length > 0) {
      backendEvents.forEach((be) => {
        const mapped = backendEventToThermalEvent(be);
        eventMap.set(mapped.event_id, mapped);
      });
    }

    return Array.from(eventMap.values());
  }, [backendEvents]);

  const isLiveBackend = Boolean(backendEvents && backendEvents.length > 0);

  // 1. Compute Playback Range dynamically based on active timeRange and catalog events
  const playbackRange = useMemo<PlaybackRange>(() => {
    return calculateWindowRange(timeRange, rawEvents);
  }, [timeRange, rawEvents]);

  // Current active playhead timestamp in ms
  const playbackTime = useMemo<number>(() => {
    if (playbackMode === "LIVE" || customPlaybackTime === null) {
      return playbackRange.end;
    }
    return Math.min(Math.max(customPlaybackTime, playbackRange.start), playbackRange.end);
  }, [playbackMode, customPlaybackTime, playbackRange]);

  // Fractional progress 0.0 to 1.0
  const playbackProgress = useMemo<number>(() => {
    if (playbackRange.durationMs <= 0) return 1.0;
    return Math.min(
      1.0,
      Math.max(0.0, (playbackTime - playbackRange.start) / playbackRange.durationMs)
    );
  }, [playbackTime, playbackRange]);

  // 2. Playback Transport Actions
  const setPlaybackProgress = useCallback(
    (progress: number) => {
      const clamped = Math.min(1.0, Math.max(0.0, progress));
      const targetTime = playbackRange.start + clamped * playbackRange.durationMs;
      setPlaybackMode("PLAYBACK");
      setCustomPlaybackTime(targetTime);
    },
    [playbackRange]
  );

  const setPlaybackTime = useCallback(
    (timeMs: number) => {
      setPlaybackMode("PLAYBACK");
      setCustomPlaybackTime(
        Math.min(Math.max(timeMs, playbackRange.start), playbackRange.end)
      );
    },
    [playbackRange]
  );

  const setTimeRange = useCallback((newRange: string) => {
    setTimeRangeState(newRange);
    // Reset playhead to live when switching time range
    setPlaybackMode("LIVE");
    setIsPlaying(false);
    setCustomPlaybackTime(null);
  }, []);

  const togglePlayPause = useCallback(() => {
    if (playbackMode === "LIVE") {
      setPlaybackMode("PLAYBACK");
      setIsPlaying(true);
      // Start from beginning of range if at live end
      setCustomPlaybackTime(playbackRange.start);
    } else {
      setIsPlaying((prev) => !prev);
    }
  }, [playbackMode, playbackRange]);

  const startPlayback = useCallback(() => {
    setPlaybackMode("PLAYBACK");
    setIsPlaying(true);
    setCustomPlaybackTime(playbackRange.start);
  }, [playbackRange]);

  const resetToLive = useCallback(() => {
    setPlaybackMode("LIVE");
    setIsPlaying(false);
    setCustomPlaybackTime(null);
  }, []);

  const stepForward = useCallback(
    (fraction = 0.05) => {
      setPlaybackMode("PLAYBACK");
      setCustomPlaybackTime((prev) => {
        const curr = prev === null ? playbackRange.end : prev;
        const next = curr + playbackRange.durationMs * fraction;
        return Math.min(next, playbackRange.end);
      });
    },
    [playbackRange]
  );

  const stepBackward = useCallback(
    (fraction = 0.05) => {
      setPlaybackMode("PLAYBACK");
      setCustomPlaybackTime((prev) => {
        const curr = prev === null ? playbackRange.end : prev;
        const next = curr - playbackRange.durationMs * fraction;
        return Math.max(next, playbackRange.start);
      });
    },
    [playbackRange]
  );

  // Playback Tick Interval loop
  useEffect(() => {
    if (!isPlaying || playbackMode !== "PLAYBACK") {
      return;
    }

    const stepIntervalMs = 50; // 20 FPS ticker
    const timer = setInterval(() => {
      setCustomPlaybackTime((prev) => {
        const curr = prev === null ? playbackRange.start : prev;
        // Advance time: 1 sec of real time advances (duration / 30s) * speed
        const baseSpeedMs = (playbackRange.durationMs / 30) * (stepIntervalMs / 1000);
        const next = curr + baseSpeedMs * playbackSpeed;

        if (next >= playbackRange.end) {
          setIsPlaying(false);
          return playbackRange.end;
        }
        return next;
      });
    }, stepIntervalMs);

    return () => clearInterval(timer);
  }, [isPlaying, playbackMode, playbackSpeed, playbackRange]);

  // Refetch wrapper: ignore backend refresh if actively playing back historical frames
  const refetch = useCallback(async () => {
    if (playbackMode === "PLAYBACK" && isPlaying) {
      return;
    }
    await rawRefetch();
  }, [playbackMode, isPlaying, rawRefetch]);

  // 3. Centralized Event Filtering (Temporal Playback + Layers + Classification + Priority + Search)
  const filteredEvents = useMemo(() => {
    // A. Filter by Temporal State & Playhead
    const temporallyFiltered = filterEventsByTemporalState(
      rawEvents,
      playbackRange,
      playbackTime,
      playbackMode === "PLAYBACK"
    );

    // B. Filter by Layers, Classification Chips, Priority, and Search
    return temporallyFiltered.filter((evt) => {
      // Layer visibility
      if (activeLayers.all_thermal === false) return false;
      if (activeLayers.industrial === false && evt.classification === "INDUSTRIAL") return false;
      if (activeLayers.non_industrial === false && evt.classification === "NON_INDUSTRIAL") return false;
      if (activeLayers.review_required === false && evt.uncertainty_state === "REVIEW_REQUIRED") return false;
      if (activeLayers.persistent_sources === true && !evt.is_persistent) return false;

      // Classification chips
      if (selectedClassification !== "ALL") {
        if (selectedClassification === "REVIEW_REQUIRED") {
          if (evt.uncertainty_state !== "REVIEW_REQUIRED") return false;
        } else if (evt.classification !== selectedClassification) {
          return false;
        }
      }

      // Operational Priority filtering
      if (selectedPriority !== "ALL") {
        const risk = calculateOperationalRisk(evt);
        if (selectedPriority === "CRITICAL" && risk.level !== "CRITICAL") return false;
        if (selectedPriority === "HIGH" && risk.level !== "HIGH") return false;
        if (selectedPriority === "MEDIUM" && risk.level !== "MEDIUM") return false;
        if (selectedPriority === "LOW" && risk.level !== "LOW") return false;
        if (
          selectedPriority === "REVIEW_REQUIRED" &&
          !risk.isIndeterminate &&
          evt.uncertainty_state !== "REVIEW_REQUIRED" &&
          evt.classification !== "UNKNOWN"
        ) {
          return false;
        }
      }

      // Search query matching
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesId = evt.event_id.toLowerCase().includes(query);
        const matchesLoc = evt.location_name?.toLowerCase().includes(query) ?? false;
        const matchesClass = evt.classification.toLowerCase().includes(query);
        const matchesContext = evt.context_summary?.toLowerCase().includes(query) ?? false;
        const matchesSource = evt.source_id?.toLowerCase().includes(query) ?? false;

        if (!matchesId && !matchesLoc && !matchesClass && !matchesContext && !matchesSource) {
          return false;
        }
      }

      return true;
    });
  }, [
    rawEvents,
    playbackRange,
    playbackTime,
    playbackMode,
    activeLayers,
    selectedClassification,
    selectedPriority,
    searchQuery,
  ]);

  // Selected event grace check: if selected event is filtered out by temporal window or playhead, gracefully deselect
  useEffect(() => {
    if (selectedEvent) {
      const stillExists = filteredEvents.some((e) => e.event_id === selectedEvent.event_id);
      if (!stillExists) {
        setSelectedEvent(null);
      }
    }
  }, [filteredEvents, selectedEvent]);

  // Compute dynamic aggregate stats reflecting current filtered events
  const stats = useMemo<EventStats>(() => {
    const total = filteredEvents.length;
    let industrial = 0;
    let nonIndustrial = 0;
    let unknown = 0;
    let reviewRequired = 0;
    let critical = 0;
    let high = 0;
    let medium = 0;
    let low = 0;
    let maxFrp = 0;

    filteredEvents.forEach((evt) => {
      if (evt.classification === "INDUSTRIAL") industrial++;
      else if (evt.classification === "NON_INDUSTRIAL") nonIndustrial++;
      else unknown++;

      if (evt.uncertainty_state === "REVIEW_REQUIRED") reviewRequired++;
      if (evt.frp_mw > maxFrp) maxFrp = evt.frp_mw;

      const risk = calculateOperationalRisk(evt);
      if (risk.level === "CRITICAL") critical++;
      else if (risk.level === "HIGH") high++;
      else if (risk.level === "MEDIUM") medium++;
      else if (risk.level === "LOW") low++;
    });

    return {
      total,
      industrial,
      nonIndustrial,
      unknown,
      reviewRequired,
      critical,
      high,
      medium,
      low,
      maxFrp,
    };
  }, [filteredEvents]);

  const resetFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedClassification("ALL");
    setSelectedPriority("ALL");
    setTimeRangeState("ALL");
    setPlaybackMode("LIVE");
    setIsPlaying(false);
    setCustomPlaybackTime(null);
    const initial: Record<string, boolean> = {};
    INITIAL_LAYERS.forEach((layer) => {
      initial[layer.id] = layer.enabled;
    });
    setActiveLayers(initial);
  }, []);

  const value = useMemo<EventContextType>(
    () => ({
      rawEvents,
      filteredEvents,
      searchQuery,
      setSearchQuery,
      selectedClassification,
      setSelectedClassification,
      selectedPriority,
      setSelectedPriority,
      selectedEvent,
      setSelectedEvent,
      isDetailOpen,
      setIsDetailOpen,
      isDossierOpen,
      setIsDossierOpen,
      isResponseCenterOpen,
      setIsResponseCenterOpen,
      activeLayers,
      toggleLayer,
      timeRange,
      setTimeRange,

      // Playback State & Controls
      playbackMode,
      isPlaying,
      playbackSpeed,
      playbackTime,
      playbackRange,
      playbackProgress,
      setPlaybackMode,
      setPlaybackTime,
      setPlaybackProgress,
      setIsPlaying,
      setPlaybackSpeed,
      togglePlayPause,
      stepForward,
      stepBackward,
      resetToLive,
      startPlayback,

      stats,
      isLiveBackend,
      isLoading,
      isFetching,
      isError,
      refetch,
      resetFilters,
    }),
    [
      rawEvents,
      filteredEvents,
      searchQuery,
      selectedClassification,
      selectedPriority,
      selectedEvent,
      isDetailOpen,
      isDossierOpen,
      isResponseCenterOpen,
      activeLayers,
      toggleLayer,
      timeRange,
      setTimeRange,

      playbackMode,
      isPlaying,
      playbackSpeed,
      playbackTime,
      playbackRange,
      playbackProgress,
      setPlaybackMode,
      setPlaybackTime,
      setPlaybackProgress,
      setIsPlaying,
      setPlaybackSpeed,
      togglePlayPause,
      stepForward,
      stepBackward,
      resetToLive,
      startPlayback,
      stats,
      isLiveBackend,
      isLoading,
      isFetching,
      isError,
      refetch,
      resetFilters,
    ]
  );

  return <EventContext.Provider value={value}>{children}</EventContext.Provider>;
}

export function useEventContext(): EventContextType {
  const context = useContext(EventContext);
  if (!context) {
    throw new Error("useEventContext must be used within an EventProvider");
  }
  return context;
}
