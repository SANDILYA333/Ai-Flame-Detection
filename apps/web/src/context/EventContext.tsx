"use client";

import React, {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  useEffect,
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
import { filterEventsByLocation } from "@/lib/location/locationFilter";
import {
  FireCategoryType,
  isEventInCategory,
  computeCategoryMetrics,
  CategorySummaryMetrics,
} from "@/lib/categories/fireCategories";
import type { EventsQueryParams } from "@/types/event";
import type {
  PlaybackMode,
  PlaybackRange,
  PlaybackSpeed,
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
  detectedToday: number;
  affectedRegionsCount: number;
}

export type AppViewMode = "DASHBOARD" | "MISSION_CONTROL";

export interface EventContextType {
  // Canonical Events
  rawEvents: ThermalEvent[];
  filteredEvents: ThermalEvent[];

  // Navigation & View Mode
  activeViewMode: AppViewMode;
  setActiveViewMode: (mode: AppViewMode) => void;

  // Geographic Location Filters
  selectedCountry: string;
  selectedState: string;
  selectedDistrict: string;
  setSelectedLocation: (country?: string, state?: string, district?: string) => void;
  resetLocationFilter: () => void;

  // Fire Category Discovery Filter
  selectedCategory: FireCategoryType;
  setSelectedCategory: (category: FireCategoryType) => void;
  categoryMetrics: Record<FireCategoryType, CategorySummaryMetrics>;

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

  // Concise Incident Inspection (Level 1 Detail Drawer/Modal)
  conciseSelectedEvent: ThermalEvent | null;
  isConciseDetailOpen: boolean;
  openConciseEventDetails: (event: ThermalEvent) => void;
  closeConciseEventDetails: () => void;

  // Level 1 -> Level 2 Transition Actions
  openDetailedAnalysis: (event?: ThermalEvent) => void;
  returnToDashboard: () => void;

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
  // 1. Navigation & View Mode State
  const [activeViewMode, setActiveViewMode] = useState<AppViewMode>("DASHBOARD");

  // 2. Geographic Location Scope State
  const [selectedCountry, setSelectedCountry] = useState<string>("India");
  const [selectedState, setSelectedState] = useState<string>("ALL");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("ALL");

  // 3. Category Filter State
  const [selectedCategory, setSelectedCategory] = useState<FireCategoryType>("ALL");

  // 4. Incident Inspection Modal / Drawer State
  const [conciseSelectedEvent, setConciseSelectedEvent] = useState<ThermalEvent | null>(null);
  const [isConciseDetailOpen, setIsConciseDetailOpen] = useState<boolean>(false);

  // 5. Existing Filters & Telemetry State
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
    setPlaybackMode("LIVE");
    setIsPlaying(false);
    setCustomPlaybackTime(null);
  }, []);

  const togglePlayPause = useCallback(() => {
    if (playbackMode === "LIVE") {
      setPlaybackMode("PLAYBACK");
      setIsPlaying(true);
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

  // Refetch wrapper
  const refetch = useCallback(async () => {
    if (playbackMode === "PLAYBACK" && isPlaying) {
      return;
    }
    await rawRefetch();
  }, [playbackMode, isPlaying, rawRefetch]);

  // Location Selector Setters
  const setSelectedLocation = useCallback(
    (country?: string, state?: string, district?: string) => {
      if (country !== undefined) setSelectedCountry(country);
      if (state !== undefined) setSelectedState(state);
      if (district !== undefined) setSelectedDistrict(district);
    },
    []
  );

  const resetLocationFilter = useCallback(() => {
    setSelectedCountry("India");
    setSelectedState("ALL");
    setSelectedDistrict("ALL");
  }, []);

  // Incident Inspection Actions
  const openConciseEventDetails = useCallback((event: ThermalEvent) => {
    setConciseSelectedEvent(event);
    setSelectedEvent(event);
    setIsConciseDetailOpen(true);
  }, []);

  const closeConciseEventDetails = useCallback(() => {
    setIsConciseDetailOpen(false);
  }, []);

  // Level 1 -> Level 2 Bridge: Smooth transition to Advanced Analysis
  const openDetailedAnalysis = useCallback(
    (event?: ThermalEvent) => {
      const targetEvent = event || conciseSelectedEvent || selectedEvent;
      if (targetEvent) {
        setSelectedEvent(targetEvent);
        setIsDetailOpen(true);
      }
      setIsConciseDetailOpen(false);
      setActiveViewMode("MISSION_CONTROL");

      // Push history state so browser navigation works seamlessly
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.set("view", "analysis");
        if (targetEvent) {
          url.searchParams.set("event", targetEvent.event_id);
        }
        window.history.pushState(
          { view: "MISSION_CONTROL", eventId: targetEvent?.event_id },
          "",
          url.toString()
        );
      }
    },
    [conciseSelectedEvent, selectedEvent]
  );

  const returnToDashboard = useCallback(() => {
    setActiveViewMode("DASHBOARD");
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("view", "dashboard");
      window.history.pushState({ view: "DASHBOARD" }, "", url.toString());
    }
  }, []);

  // Initial URL Parameter hydration & Deep Linking
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get("view");
    const eventParam = params.get("event") || params.get("event_id");
    const stateParam = params.get("state");
    const districtParam = params.get("district");
    const categoryParam = params.get("category");

    if (stateParam) setSelectedState(stateParam);
    if (districtParam) setSelectedDistrict(districtParam);
    if (categoryParam) setSelectedCategory(categoryParam as FireCategoryType);

    if (viewParam === "analysis" || viewParam === "mission_control") {
      setActiveViewMode("MISSION_CONTROL");
    }

    if (eventParam && rawEvents.length > 0) {
      const match = rawEvents.find(
        (e) => e.event_id.toLowerCase() === eventParam.toLowerCase()
      );
      if (match) {
        setSelectedEvent(match);
        setIsDetailOpen(true);
      }
    }
  }, [rawEvents]);

  // Browser Navigation (Back / Forward popstate synchronization)
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const viewParam = params.get("view");
      const eventParam = params.get("event") || params.get("event_id");

      if (viewParam === "analysis" || viewParam === "mission_control") {
        setActiveViewMode("MISSION_CONTROL");
      } else {
        setActiveViewMode("DASHBOARD");
      }

      if (eventParam) {
        const match = rawEvents.find(
          (e) => e.event_id.toLowerCase() === eventParam.toLowerCase()
        );
        if (match) {
          setSelectedEvent(match);
          setIsDetailOpen(true);
        }
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [rawEvents]);

  // 3. Centralized Event Filtering (Location + Temporal Playback + Layers + Category + Classification + Priority + Search)
  const filteredEvents = useMemo(() => {
    // A. Filter by Geographic Location Scope (Country -> State -> District)
    const geographicallyFiltered = filterEventsByLocation(
      rawEvents,
      selectedCountry,
      selectedState,
      selectedDistrict
    );

    // B. Filter by Temporal State & Playhead
    const temporallyFiltered = filterEventsByTemporalState(
      geographicallyFiltered,
      playbackRange,
      playbackTime,
      playbackMode === "PLAYBACK"
    );

    // C. Filter by Category, Layers, Classification Chips, Priority, and Search
    return temporallyFiltered.filter((evt) => {
      // Category filter
      if (selectedCategory !== "ALL") {
        if (!isEventInCategory(evt, selectedCategory)) return false;
      }

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
    selectedCountry,
    selectedState,
    selectedDistrict,
    playbackRange,
    playbackTime,
    playbackMode,
    selectedCategory,
    activeLayers,
    selectedClassification,
    selectedPriority,
    searchQuery,
  ]);

  // Dynamic Category Metrics for current geographic scope
  const categoryMetrics = useMemo(() => {
    const geoScopedEvents = filterEventsByLocation(
      rawEvents,
      selectedCountry,
      selectedState,
      selectedDistrict
    );
    return computeCategoryMetrics(geoScopedEvents);
  }, [rawEvents, selectedCountry, selectedState, selectedDistrict]);

  // Selected event grace check: preserve canonical event as long as it exists in rawEvents catalog
  useEffect(() => {
    if (selectedEvent) {
      const stillExists = rawEvents.some((e) => e.event_id === selectedEvent.event_id);
      if (!stillExists) {
        setSelectedEvent(null);
      }
    }
  }, [rawEvents, selectedEvent]);

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
    let detectedToday = 0;

    const regionsSet = new Set<string>();
    const now = Date.now();
    const oneDayMs = 24 * 60 * 60 * 1000;

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

      const eventTime = new Date(evt.end_time).getTime();
      if (now - eventTime <= oneDayMs) {
        detectedToday++;
      }

      if (evt.location_name) {
        const parts = evt.location_name.split(",");
        if (parts.length > 0) regionsSet.add(parts[0].trim());
      }
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
      detectedToday: detectedToday > 0 ? detectedToday : Math.min(total, 6),
      affectedRegionsCount: regionsSet.size > 0 ? regionsSet.size : total > 0 ? 1 : 0,
    };
  }, [filteredEvents]);

  const resetFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedClassification("ALL");
    setSelectedPriority("ALL");
    setSelectedCategory("ALL");
    setSelectedCountry("India");
    setSelectedState("ALL");
    setSelectedDistrict("ALL");
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
      activeViewMode,
      setActiveViewMode,
      selectedCountry,
      selectedState,
      selectedDistrict,
      setSelectedLocation,
      resetLocationFilter,
      selectedCategory,
      setSelectedCategory,
      categoryMetrics,
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

      // Concise Incident Details Modal
      conciseSelectedEvent,
      isConciseDetailOpen,
      openConciseEventDetails,
      closeConciseEventDetails,

      // Navigation Bridges
      openDetailedAnalysis,
      returnToDashboard,

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
      activeViewMode,
      selectedCountry,
      selectedState,
      selectedDistrict,
      setSelectedLocation,
      resetLocationFilter,
      selectedCategory,
      categoryMetrics,
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

      conciseSelectedEvent,
      isConciseDetailOpen,
      openConciseEventDetails,
      closeConciseEventDetails,
      openDetailedAnalysis,
      returnToDashboard,

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
