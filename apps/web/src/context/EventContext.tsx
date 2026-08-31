"use client";

import React, { createContext, useContext, useState, useMemo, useCallback } from "react";
import { useEvents } from "@/hooks/useEvents";
import { backendEventToThermalEvent, ThermalEvent } from "@/types/event";
import { DEMO_THERMAL_EVENTS } from "@/features/events/mock/demo-events";
import { INITIAL_LAYERS } from "@/config/ui";

export interface EventStats {
  total: number;
  industrial: number;
  nonIndustrial: number;
  unknown: number;
  reviewRequired: number;
  maxFrp: number;
}

export interface EventContextType {
  rawEvents: ThermalEvent[];
  filteredEvents: ThermalEvent[];
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
  stats: EventStats;
  isLiveBackend: boolean;
  isLoading: boolean;
  isError: boolean;
  resetFilters: () => void;
}

const EventContext = createContext<EventContextType | undefined>(undefined);

export function EventProvider({ children }: { children: React.ReactNode }) {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedClassification, setSelectedClassification] = useState<string>("ALL");
  const [selectedEvent, setSelectedEvent] = useState<ThermalEvent | null>(null);
  const [timeRange, setTimeRange] = useState<string>("24h");

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
  const { events: backendEvents, isLoading, isError } = useEvents({ limit: 100 });

  // Map backend events to ThermalEvent, or fallback to deterministic demo catalog
  const rawEvents = useMemo(() => {
    if (backendEvents && backendEvents.length > 0) {
      return backendEvents.map(backendEventToThermalEvent);
    }
    return DEMO_THERMAL_EVENTS;
  }, [backendEvents]);

  const isLiveBackend = Boolean(backendEvents && backendEvents.length > 0);

  // Compute live aggregate stats
  const stats = useMemo<EventStats>(() => {
    const total = rawEvents.length;
    let industrial = 0;
    let nonIndustrial = 0;
    let unknown = 0;
    let reviewRequired = 0;
    let maxFrp = 0;

    rawEvents.forEach((evt) => {
      if (evt.classification === "INDUSTRIAL") industrial++;
      else if (evt.classification === "NON_INDUSTRIAL") nonIndustrial++;
      else unknown++;

      if (evt.uncertainty_state === "REVIEW_REQUIRED") reviewRequired++;
      if (evt.frp_mw > maxFrp) maxFrp = evt.frp_mw;
    });

    return { total, industrial, nonIndustrial, unknown, reviewRequired, maxFrp };
  }, [rawEvents]);

  // Filter events by Search Query, Layer Toggles, and Classification Chips
  const filteredEvents = useMemo(() => {
    return rawEvents.filter((evt) => {
      // 1. Layer visibility filtering
      if (activeLayers.all_thermal === false) return false;
      if (activeLayers.industrial === false && evt.classification === "INDUSTRIAL") return false;
      if (activeLayers.non_industrial === false && evt.classification === "NON_INDUSTRIAL") return false;
      if (activeLayers.review_required === false && evt.uncertainty_state === "REVIEW_REQUIRED") return false;
      if (activeLayers.persistent_sources === true && !evt.is_persistent) return false;

      // 2. Classification chip filtering
      if (selectedClassification !== "ALL") {
        if (selectedClassification === "REVIEW_REQUIRED") {
          if (evt.uncertainty_state !== "REVIEW_REQUIRED") return false;
        } else if (evt.classification !== selectedClassification) {
          return false;
        }
      }

      // 3. Search query matching
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
  }, [rawEvents, activeLayers, selectedClassification, searchQuery]);

  const resetFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedClassification("ALL");
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
      stats,
      isLiveBackend,
      isLoading,
      isError,
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
      stats,
      isLiveBackend,
      isLoading,
      isError,
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
