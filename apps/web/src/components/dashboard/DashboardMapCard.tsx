"use client";

import React, { useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import { useEventContext } from "@/context/EventContext";
import { STATE_BOUNDS_MAP, DEFAULT_INDIA_VIEW } from "@/lib/location/locationFilter";
import { Map, Maximize2, Crosshair, Flame, Radio } from "lucide-react";
import type { FlatMapViewHandle } from "@/components/map/FlatMapView";
import type { ThermalEvent } from "@/types/event";

const FlatMapView = dynamic(
  () => import("@/components/map/FlatMapView").then((mod) => mod.FlatMapView),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex flex-col items-center justify-center bg-base text-foreground-muted font-mono text-xs">
        <div className="w-6 h-6 rounded-full border-2 border-accent/20 border-t-accent animate-spin mb-2" />
        <span>LOADING SPATIAL OVERVIEW...</span>
      </div>
    ),
  }
);

export function DashboardMapCard() {
  const {
    filteredEvents,
    selectedEvent,
    setSelectedEvent,
    openConciseEventDetails,
    openDetailedAnalysis,
    selectedState,
    selectedCountry,
  } = useEventContext();

  const flatMapRef = useRef<FlatMapViewHandle>(null);

  // Determine center coordinates and zoom level based on active state or country filter
  const { centerLat, centerLng, initialZoom } = useMemo(() => {
    if (selectedState !== "ALL" && STATE_BOUNDS_MAP[selectedState]) {
      const bounds = STATE_BOUNDS_MAP[selectedState];
      return {
        centerLat: bounds.center[0],
        centerLng: bounds.center[1],
        initialZoom: bounds.zoom,
      };
    }
    return {
      centerLat: DEFAULT_INDIA_VIEW.center[0],
      centerLng: DEFAULT_INDIA_VIEW.center[1],
      initialZoom: DEFAULT_INDIA_VIEW.zoom,
    };
  }, [selectedState]);

  const handleSelectEvent = (event: ThermalEvent) => {
    setSelectedEvent(event);
    openConciseEventDetails(event);
  };

  return (
    <div className="bg-surface border border-border rounded-panel overflow-hidden shadow-panel flex flex-col h-[420px] font-mono">
      {/* Map Header */}
      <div className="h-10 px-3.5 bg-surface-raised border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-xs">
          <Map className="w-3.5 h-3.5 text-accent-cyan" />
          <span className="font-bold text-foreground uppercase tracking-wider">
            GEOSPATIAL SITUATIONAL MAP
          </span>
          <span className="text-[10px] text-foreground-muted hidden sm:inline">
            · {selectedState !== "ALL" ? selectedState : selectedCountry} Region
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1 text-[10px] text-thermal font-semibold px-2 py-0.5 rounded bg-thermal/10 border border-thermal/30">
            <Flame className="w-3 h-3 animate-flame" />
            <span>{filteredEvents.length} Active Pins</span>
          </div>

          <button
            onClick={() => openDetailedAnalysis()}
            title="Open in Advanced Mission Control"
            className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded bg-accent/15 hover:bg-accent/25 border border-accent/40 text-accent transition-colors"
          >
            <Maximize2 className="w-3 h-3" />
            <span className="hidden sm:inline">EXPAND FULL MAP</span>
          </button>
        </div>
      </div>

      {/* Map Canvas Body */}
      <div className="relative flex-1 w-full h-full bg-base overflow-hidden">
        <FlatMapView
          key={`${selectedState}-${selectedCountry}`}
          ref={flatMapRef}
          initialLat={centerLat}
          initialLng={centerLng}
          initialZoom={initialZoom}
          events={filteredEvents}
          selectedEvent={selectedEvent}
          isVisible={true}
          onSelectEvent={handleSelectEvent}
        />

        {/* Floating Quick Legend */}
        <div className="absolute bottom-2.5 left-2.5 z-10 bg-surface/85 backdrop-blur-md px-2.5 py-1.5 rounded-control border border-border text-[10px] text-foreground-secondary flex items-center gap-3 shadow-panel">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-thermal" />
            <span>Active Fire</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-accent" />
            <span>Industrial</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#34c759]" />
            <span>Wildfire</span>
          </div>
        </div>
      </div>
    </div>
  );
}
