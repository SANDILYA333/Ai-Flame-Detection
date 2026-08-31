"use client";

import React, { useState, useCallback, useMemo, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { ViewModeToggle, ViewMode } from "./ViewModeToggle";
import { MapControls } from "./MapControls";
import { LayerPanelPlaceholder } from "./LayerPanelPlaceholder";
import { EventIntelligenceFeed } from "@/components/events/EventIntelligenceFeed";
import { EventIntelligencePanel } from "@/components/events/EventIntelligencePanel";
import { TimelinePlaybackBar } from "@/components/playback/TimelinePlaybackBar";
import { MapOverlayContainer } from "./MapOverlayContainer";
import { useEventContext } from "@/context/EventContext";
import { ThermalEvent } from "@/types/event";
import { Compass, Crosshair, Flame, ShieldCheck, Wifi, AlertTriangle, RotateCcw } from "lucide-react";
import { APP_CONFIG } from "@/config/ui";
import { formatCoordinate } from "@/lib/format/coordinates";
import { cn } from "@/lib/utils";
import type { GlobeViewHandle } from "./GlobeView";
import type { FlatMapViewHandle } from "./FlatMapView";

// Dynamically import WebGL renderers to ensure SSR safety
const GlobeView = dynamic(
  () => import("./GlobeView").then((mod) => mod.GlobeView),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex flex-col items-center justify-center bg-background text-foreground-muted font-mono text-xs">
        <div className="w-8 h-8 rounded-full border-2 border-accent/20 border-t-accent animate-spin mb-3" />
        <span>INITIALIZING 3D ORBITAL ENGINE...</span>
      </div>
    ),
  }
);

const FlatMapView = dynamic(
  () => import("./FlatMapView").then((mod) => mod.FlatMapView),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex flex-col items-center justify-center bg-background text-foreground-muted font-mono text-xs">
        <div className="w-8 h-8 rounded-full border-2 border-accent/20 border-t-accent animate-spin mb-3" />
        <span>LOADING 2D GEOSPATIAL CARTOGRAPHY...</span>
      </div>
    ),
  }
);

export interface MapWorkspaceProps {
  className?: string;
}

export function MapWorkspace({ className }: MapWorkspaceProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("2D");
  const [showLayers, setShowLayers] = useState(false);
  const [showIntel, setShowIntel] = useState(false);

  const {
    filteredEvents,
    rawEvents,
    selectedEvent,
    setSelectedEvent,
    isLiveBackend,
    resetFilters,
  } = useEventContext();

  // Current selected event index for Next/Prev navigation
  const selectedIndex = useMemo(() => {
    if (!selectedEvent) return -1;
    return filteredEvents.findIndex((e) => e.event_id === selectedEvent.event_id);
  }, [filteredEvents, selectedEvent]);

  // Select initial anchor event once events are loaded
  useEffect(() => {
    if (!selectedEvent && filteredEvents.length > 0) {
      setSelectedEvent(filteredEvents[0]);
    }
  }, [filteredEvents, selectedEvent, setSelectedEvent]);

  const globeRef = useRef<GlobeViewHandle>(null);
  const flatRef = useRef<FlatMapViewHandle>(null);

  const [cameraState, setCameraState] = useState({
    lat: APP_CONFIG.defaultCenter.lat,
    lng: APP_CONFIG.defaultCenter.lon,
    zoom: APP_CONFIG.defaultCenter.zoom,
  });

  const handleCameraChange = useCallback((lat: number, lng: number, zoom: number) => {
    setCameraState({ lat, lng, zoom });
  }, []);

  const handleSelectEvent = useCallback(
    (event: ThermalEvent) => {
      setSelectedEvent(event);
      setCameraState({
        lat: event.latitude,
        lng: event.longitude,
        zoom: 8.5,
      });
    },
    [setSelectedEvent]
  );

  const handlePrevEvent = useCallback(() => {
    if (filteredEvents.length === 0) return;
    const nextIdx = selectedIndex <= 0 ? filteredEvents.length - 1 : selectedIndex - 1;
    handleSelectEvent(filteredEvents[nextIdx]);
  }, [filteredEvents, selectedIndex, handleSelectEvent]);

  const handleNextEvent = useCallback(() => {
    if (filteredEvents.length === 0) return;
    const nextIdx = selectedIndex >= filteredEvents.length - 1 ? 0 : selectedIndex + 1;
    handleSelectEvent(filteredEvents[nextIdx]);
  }, [filteredEvents, selectedIndex, handleSelectEvent]);

  const handleCenterSelected = useCallback(() => {
    if (!selectedEvent) return;
    setCameraState({
      lat: selectedEvent.latitude,
      lng: selectedEvent.longitude,
      zoom: 8.5,
    });
  }, [selectedEvent]);

  // Global Keyboard Shortcuts (Left/Right arrow for navigation, Space for play/pause, Esc to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Avoid intercepting if focus is on an input or textarea
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrevEvent();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNextEvent();
      } else if (e.key === "Escape") {
        if (selectedEvent) {
          setSelectedEvent(null);
        } else if (showIntel) {
          setShowIntel(false);
        } else if (showLayers) {
          setShowLayers(false);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePrevEvent, handleNextEvent, selectedEvent, setSelectedEvent, showIntel, showLayers]);

  const handleZoomIn = useCallback(() => {
    if (viewMode === "3D") {
      globeRef.current?.zoomIn();
    } else {
      flatRef.current?.zoomIn();
    }
  }, [viewMode]);

  const handleZoomOut = useCallback(() => {
    if (viewMode === "3D") {
      globeRef.current?.zoomOut();
    } else {
      flatRef.current?.zoomOut();
    }
  }, [viewMode]);

  const handleResetHome = useCallback(() => {
    setSelectedEvent(null);
    if (viewMode === "3D") {
      globeRef.current?.resetView();
    } else {
      flatRef.current?.resetView();
    }
    setCameraState({
      lat: APP_CONFIG.defaultCenter.lat,
      lng: APP_CONFIG.defaultCenter.lon,
      zoom: APP_CONFIG.defaultCenter.zoom,
    });
  }, [viewMode, setSelectedEvent]);

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
    if (mode === "2D") {
      flatRef.current?.resize();
    }
    setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
      if (mode === "2D") {
        flatRef.current?.resize();
      }
    }, 60);
  }, []);

  // Display coordinates: prioritize selected target datum or active center datum
  const displayCoordinates = useMemo(() => {
    if (selectedEvent) {
      return formatCoordinate(selectedEvent.latitude, selectedEvent.longitude);
    }
    return formatCoordinate(cameraState.lat, cameraState.lng);
  }, [selectedEvent, cameraState.lat, cameraState.lng]);

  return (
    <div className={cn("relative w-full h-full overflow-hidden bg-background select-none", className)}>
      {/* 1. Geospatial Rendering Canvases */}
      <div className="absolute inset-0 z-0">
        <div
          className={cn(
            "absolute inset-0 transition-opacity duration-200",
            viewMode === "3D"
              ? "opacity-100 pointer-events-auto z-10"
              : "opacity-0 pointer-events-none z-0"
          )}
        >
          <GlobeView
            ref={globeRef}
            initialLat={APP_CONFIG.defaultCenter.lat}
            initialLng={APP_CONFIG.defaultCenter.lon}
            events={filteredEvents}
            selectedEvent={selectedEvent}
            isVisible={viewMode === "3D"}
            onSelectEvent={handleSelectEvent}
            onCameraChange={handleCameraChange}
            onSwitchTo2D={() => handleViewModeChange("2D")}
          />
        </div>

        <div
          className={cn(
            "absolute inset-0 transition-opacity duration-200",
            viewMode === "2D"
              ? "opacity-100 pointer-events-auto z-10"
              : "opacity-0 pointer-events-none z-0"
          )}
        >
          <FlatMapView
            ref={flatRef}
            initialLat={APP_CONFIG.defaultCenter.lat}
            initialLng={APP_CONFIG.defaultCenter.lon}
            initialZoom={APP_CONFIG.defaultCenter.zoom}
            events={filteredEvents}
            selectedEvent={selectedEvent}
            isVisible={viewMode === "2D"}
            onSelectEvent={handleSelectEvent}
            onCameraChange={handleCameraChange}
          />
        </div>
      </div>

      {/* 2. Empty Filter State Notification Banner */}
      {filteredEvents.length === 0 && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30 bg-surface-raised/95 backdrop-blur-md border border-border px-4 py-2.5 rounded-panel shadow-panel flex items-center gap-3 font-mono text-xs text-foreground-muted animate-in fade-in zoom-in-95 duration-150">
          <AlertTriangle className="w-4 h-4 text-state-warning shrink-0" />
          <span>No thermal events in this time window ({rawEvents.length} in catalog).</span>
          <button
            onClick={resetFilters}
            className="flex items-center gap-1 px-2.5 py-1 rounded-control bg-accent/15 border border-accent/30 text-accent hover:bg-accent/25 transition-colors font-semibold"
          >
            <RotateCcw className="w-3 h-3" />
            Reset Filters
          </button>
        </div>
      )}

      {/* 3. Structured Overlay Architecture */}
      <MapOverlayContainer
        hud={
          <div className="flex items-center justify-between pointer-events-none">
            {/* Left Telemetry HUD */}
            <div className="pointer-events-auto flex items-center gap-2 bg-surface/85 backdrop-blur-md px-3 py-1.5 rounded-control border border-border text-[11px] font-mono text-foreground-secondary shadow-panel">
              <Crosshair className="w-3.5 h-3.5 text-accent-cyan" />
              <span>{displayCoordinates}</span>
              <span className="text-border-strong">|</span>
              <span className="text-thermal-primary font-semibold flex items-center gap-1">
                <Flame className="w-3 h-3 animate-flame" />
                {filteredEvents.length} ACTIVE
              </span>
              <span className="text-border-strong">|</span>
              <span className="flex items-center gap-1 text-[10px] text-accent">
                <Wifi className="w-3 h-3 text-accent" />
                {isLiveBackend ? "LIVE FASTAPI" : "MULTI-SOURCE READY"}
              </span>
            </div>

            {/* Center: 2D / 3D Mode Toggle */}
            <div className="pointer-events-auto">
              <ViewModeToggle mode={viewMode} onChange={handleViewModeChange} />
            </div>

            {/* Right: Quick Intelligence Panel Toggle */}
            <div className="pointer-events-auto flex items-center gap-2">
              <button
                onClick={() => setShowIntel(!showIntel)}
                className={cn(
                  "h-8 px-3 text-xs font-mono rounded-control border transition-colors flex items-center gap-1.5 shadow-panel",
                  showIntel
                    ? "bg-accent/15 border-accent text-accent"
                    : "bg-surface/85 border-border text-foreground-secondary hover:text-foreground"
                )}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">LIVE FEED</span>
              </button>
            </div>
          </div>
        }
        leftPanel={
          showLayers ? (
            <LayerPanelPlaceholder onClose={() => setShowLayers(false)} />
          ) : null
        }
        rightPanel={
          showIntel ? (
            <EventIntelligenceFeed
              events={filteredEvents}
              selectedEvent={selectedEvent}
              onSelectEvent={handleSelectEvent}
              onClose={() => setShowIntel(false)}
            />
          ) : null
        }
        selectedEventCard={
          selectedEvent ? (
            <EventIntelligencePanel
              event={selectedEvent}
              currentIndex={selectedIndex >= 0 ? selectedIndex : 0}
              totalEvents={filteredEvents.length}
              onPrevEvent={handlePrevEvent}
              onNextEvent={handleNextEvent}
              onCenterMap={handleCenterSelected}
              onClose={() => setSelectedEvent(null)}
            />
          ) : null
        }
        controls={
          <MapControls
            layersActive={showLayers}
            onToggleLayers={() => setShowLayers(!showLayers)}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onResetHome={handleResetHome}
          />
        }
      >
        {/* Floating Bottom Timeline Playback Bar */}
        <div className="absolute bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 w-[96%] sm:w-[640px] max-w-[96vw] z-30">
          <TimelinePlaybackBar />
        </div>

        {/* Geographic Projection & Datum annotation */}
        <div className="absolute bottom-3 left-3 z-20 pointer-events-none hidden lg:flex items-center gap-2 bg-surface/75 backdrop-blur-md px-2.5 py-1.5 rounded-control border border-border/80 text-[10px] font-mono text-foreground-muted">
          <Compass className="w-3.5 h-3.5 text-accent-cyan animate-pulse-subtle" />
          <span>WGS-84 · EPSG:4326 · {viewMode === "3D" ? "ORTHOGRAPHIC" : "MERCATOR"}</span>
        </div>
      </MapOverlayContainer>
    </div>
  );
}
