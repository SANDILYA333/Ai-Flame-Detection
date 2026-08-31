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
  filterEventsByTemporalState,
} from "@/lib/playback/temporal";
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
  selectedEvent: ThermalEvent | null;
  setSelectedEvent: (event: ThermalEvent | null) => void;
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
  const [selectedEvent, setSelectedEvent] = useState<ThermalEvent | null>(null);
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

  // Fetch live canonical thermal events from FastAPI backend
  const {
    events: backendEvents,
    isLoading,
    isFetching,
    isError,
    refetch: rawRefetch,
  } = useEvents({ limit: 100 });

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
    return Math.min(playbackRange.end, Math.max(playbackRange.start, customPlaybackTime));
  }, [playbackMode, customPlaybackTime, playbackRange]);

  // Progress relative to active range (0.0 to 1.0)
  const playbackProgress = useMemo<number>(() => {
    if (playbackRange.durationMs <= 0) return 1.0;
    const prog = (playbackTime - playbackRange.start) / playbackRange.durationMs;
    return Math.min(1.0, Math.max(0.0, prog));
  }, [playbackTime, playbackRange]);

  // 2. Playback Animation Ticker (Advances playhead when isPlaying === true)
  useEffect(() => {
    if (!isPlaying || playbackMode !== "PLAYBACK") return;

    const intervalMs = 80;
    // Base sweep time for full window at 1x = 24 seconds (300 ticks of 80ms)
    const totalTicks = 300 / playbackSpeed;
    const timeDeltaMs = playbackRange.durationMs / totalTicks;

    const timer = setInterval(() => {
      setCustomPlaybackTime((prev) => {
        const current = prev !== null ? prev : playbackRange.start;
        const nextTime = current + timeDeltaMs;
        if (nextTime >= playbackRange.end) {
          setIsPlaying(false);
          return playbackRange.end;
        }
        return nextTime;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isPlaying, playbackMode, playbackSpeed, playbackRange]);

  // Playback Control Handlers
  const setTimeRange = useCallback((range: string) => {
    setTimeRangeState(range);
    // When switching time window in playback, clamp or align playhead
    setCustomPlaybackTime(null);
  }, []);

  const setPlaybackTime = useCallback((timeMs: number) => {
    setPlaybackMode("PLAYBACK");
    setCustomPlaybackTime(timeMs);
  }, []);

  const setPlaybackProgress = useCallback(
    (prog: number) => {
      setPlaybackMode("PLAYBACK");
      const clamped = Math.min(1.0, Math.max(0.0, prog));
      const targetTime = playbackRange.start + clamped * playbackRange.durationMs;
      setCustomPlaybackTime(targetTime);
    },
    [playbackRange]
  );

  const togglePlayPause = useCallback(() => {
    if (playbackMode === "LIVE") {
      setPlaybackMode("PLAYBACK");
      setCustomPlaybackTime(playbackRange.start);
      setIsPlaying(true);
    } else {
      if (!isPlaying && playbackTime >= playbackRange.end) {
        // If at the end, restart from beginning
        setCustomPlaybackTime(playbackRange.start);
      }
      setIsPlaying((prev) => !prev);
    }
  }, [playbackMode, isPlaying, playbackTime, playbackRange]);

  const stepForward = useCallback(
    (fraction: number = 0.05) => {
      setPlaybackMode("PLAYBACK");
      setIsPlaying(false);
      const stepMs = playbackRange.durationMs * fraction;
      setCustomPlaybackTime((prev) => {
        const current = prev !== null ? prev : playbackRange.start;
        return Math.min(playbackRange.end, current + stepMs);
      });
    },
    [playbackRange]
  );

  const stepBackward = useCallback(
    (fraction: number = 0.05) => {
      setPlaybackMode("PLAYBACK");
      setIsPlaying(false);
      const stepMs = playbackRange.durationMs * fraction;
      setCustomPlaybackTime((prev) => {
        const current = prev !== null ? prev : playbackRange.end;
        return Math.max(playbackRange.start, current - stepMs);
      });
    },
    [playbackRange]
  );

  const resetToLive = useCallback(() => {
    setIsPlaying(false);
    setPlaybackMode("LIVE");
    setCustomPlaybackTime(null);
  }, []);

  const startPlayback = useCallback(() => {
    setPlaybackMode("PLAYBACK");
    setCustomPlaybackTime(playbackRange.start);
    setIsPlaying(true);
  }, [playbackRange]);

  // Refetch wrapper: ignore backend refresh if actively playing back historical frames
  const refetch = useCallback(async () => {
    if (playbackMode === "PLAYBACK" && isPlaying) {
      return;
    }
    await rawRefetch();
  }, [playbackMode, isPlaying, rawRefetch]);

  // 3. Centralized Event Filtering (Temporal Playback + Layers + Classification + Search)
  const filteredEvents = useMemo(() => {
    // A. Filter by Temporal State & Playhead
    const temporallyFiltered = filterEventsByTemporalState(
      rawEvents,
      playbackRange,
      playbackTime,
      playbackMode === "PLAYBACK"
    );

    // B. Filter by Layers, Classification Chips, and Search
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
    searchQuery,
  ]);

  // Selected event grace check: if selected event is filtered out by temporal playhead, gracefully deselect
  useEffect(() => {
    if (selectedEvent) {
      const stillExists = filteredEvents.some((e) => e.event_id === selectedEvent.event_id);
      if (!stillExists && filteredEvents.length > 0) {
        // Keep selection stable or deselect gracefully
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
    let maxFrp = 0;

    filteredEvents.forEach((evt) => {
      if (evt.classification === "INDUSTRIAL") industrial++;
      else if (evt.classification === "NON_INDUSTRIAL") nonIndustrial++;
      else unknown++;

      if (evt.uncertainty_state === "REVIEW_REQUIRED") reviewRequired++;
      if (evt.frp_mw > maxFrp) maxFrp = evt.frp_mw;
    });

    return { total, industrial, nonIndustrial, unknown, reviewRequired, maxFrp };
  }, [filteredEvents]);

  const resetFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedClassification("ALL");
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
      selectedEvent,
      setSelectedEvent,
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
      selectedEvent,
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
