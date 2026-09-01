"use client";

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MAPLIBRE_CONFIG } from "@/lib/map/maplibre-config";
import { ThermalEvent } from "@/types/event";
import { createFireMarkerElement, updateFireMarkerSelection } from "./FireMarkerElement";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

// Configure MapLibre Web Worker URL explicitly to avoid localhost HTML fallback
if (typeof window !== "undefined" && typeof (maplibregl as any).setWorkerUrl === "function") {
  try {
    (maplibregl as any).setWorkerUrl("/maplibre-gl-worker.mjs");
  } catch (err) {
    console.warn("MapLibre setWorkerUrl fallback:", err);
  }
}

export interface FlatMapViewProps {
  initialLat?: number;
  initialLng?: number;
  initialZoom?: number;
  events?: ThermalEvent[];
  selectedEvent?: ThermalEvent | null;
  isVisible?: boolean;
  onSelectEvent?: (event: ThermalEvent) => void;
  onCameraChange?: (lat: number, lng: number, zoom: number) => void;
  className?: string;
}

export interface FlatMapViewHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
  resize: () => void;
  getMapInstance: () => maplibregl.Map | null;
}

export const FlatMapView = forwardRef<FlatMapViewHandle, FlatMapViewProps>(
  function FlatMapView(
    {
      initialLat = MAPLIBRE_CONFIG.initialCenter[1],
      initialLng = MAPLIBRE_CONFIG.initialCenter[0],
      initialZoom = MAPLIBRE_CONFIG.initialZoom,
      events = [],
      selectedEvent,
      isVisible = true,
      onSelectEvent,
      onCameraChange,
      className,
    }: FlatMapViewProps,
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<maplibregl.Map | null>(null);
    const markerMapRef = useRef<
      Map<
        string,
        {
          marker: maplibregl.Marker;
          element: HTMLElement;
          event: ThermalEvent;
          isSelected: boolean;
        }
      >
    >(new Map());
    const [isLoaded, setIsLoaded] = useState(false);
    const [hasError, setHasError] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [initCount, setInitCount] = useState(0);
    const fallbackAttemptedRef = useRef(false);

    const initialCameraRef = useRef({
      lat: initialLat,
      lng: initialLng,
      zoom: initialZoom,
    });

    // Stable callback refs
    const onCameraChangeRef = useRef(onCameraChange);
    onCameraChangeRef.current = onCameraChange;

    const onSelectEventRef = useRef(onSelectEvent);
    onSelectEventRef.current = onSelectEvent;

    // Expose imperative navigation handles
    useImperativeHandle(
      ref,
      () => ({
        zoomIn: () => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.zoomIn({ duration: 300 });
          }
        },
        zoomOut: () => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.zoomOut({ duration: 300 });
          }
        },
        resetView: () => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.flyTo({
              center: [initialCameraRef.current.lng, initialCameraRef.current.lat],
              zoom: initialCameraRef.current.zoom,
              duration: 1000,
              essential: true,
            });
          }
        },
        resize: () => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.resize();
          }
        },
        getMapInstance: () => mapInstanceRef.current,
      }),
      []
    );

    // Initialize MapLibre GL Map
    const initializeMap = () => {
      if (!containerRef.current) return;

      // Clean up any existing instance
      if (mapInstanceRef.current) {
        try {
          markerMapRef.current.forEach((rec) => rec.marker.remove());
          markerMapRef.current.clear();
          mapInstanceRef.current.remove();
        } catch {}
        mapInstanceRef.current = null;
      }

      setIsLoaded(false);
      setHasError(false);
      setErrorMessage(null);
      fallbackAttemptedRef.current = false;

      try {
        if (typeof window !== "undefined" && typeof (maplibregl as any).setWorkerUrl === "function") {
          try {
            (maplibregl as any).setWorkerUrl("/maplibre-gl-worker.mjs");
          } catch {}
        }

        const map = new maplibregl.Map({
          container: containerRef.current,
          style: MAPLIBRE_CONFIG.style,
          center: [initialCameraRef.current.lng, initialCameraRef.current.lat],
          zoom: initialCameraRef.current.zoom,
          minZoom: MAPLIBRE_CONFIG.minZoom,
          maxZoom: MAPLIBRE_CONFIG.maxZoom,
          attributionControl: false,
        });

        mapInstanceRef.current = map;

        const markLoaded = () => {
          setIsLoaded(true);
          setHasError(false);
          map.resize();
        };

        if (map.loaded()) {
          markLoaded();
        } else {
          map.once("load", markLoaded);
          map.once("styledata", markLoaded);
        }

        // Resilient style error handler: automatic seamless fallback to ESRI Dark Canvas
        map.on("error", (e) => {
          const isStyleOrTileError =
            !fallbackAttemptedRef.current &&
            (e.error?.message?.toLowerCase().includes("style") ||
              e.error?.message?.toLowerCase().includes("tile") ||
              e.error?.message?.toLowerCase().includes("fetch") ||
              (e as any).status === 404 ||
              (e as any).status === 0);

          if (isStyleOrTileError) {
            fallbackAttemptedRef.current = true;
            console.warn("MapLibre primary vector style error, applying resilient ESRI raster fallback:", e);
            try {
              map.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
              markLoaded();
            } catch (fallbackErr) {
              console.error("MapLibre fallback style also failed:", fallbackErr);
              setHasError(true);
              setErrorMessage("Unable to initialize cartography raster or vector tiles.");
            }
          }
        });

        // Timeout safety: if primary style has not resolved after 2500ms, auto-apply fallback
        const safetyTimer = setTimeout(() => {
          if (!map.loaded() && !fallbackAttemptedRef.current) {
            fallbackAttemptedRef.current = true;
            console.warn("MapLibre primary style timeout, switching to resilient ESRI fallback");
            try {
              map.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
              markLoaded();
            } catch (fallbackErr) {
              console.error("MapLibre fallback on timeout failed:", fallbackErr);
              setHasError(true);
            }
          }
        }, 2500);

        map.on("moveend", () => {
          if (onCameraChangeRef.current) {
            const center = map.getCenter();
            const zoom = map.getZoom();
            onCameraChangeRef.current(center.lat, center.lng, zoom);
          }
        });

        const resizeObserver = new ResizeObserver(() => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.resize();
          }
        });

        resizeObserver.observe(containerRef.current);

        return () => {
          clearTimeout(safetyTimer);
          resizeObserver.disconnect();
          markerMapRef.current.forEach((rec) => rec.marker.remove());
          markerMapRef.current.clear();
          if (mapInstanceRef.current) {
            mapInstanceRef.current.remove();
            mapInstanceRef.current = null;
          }
        };
      } catch (err) {
        console.error("Failed to initialize MapLibre GL:", err);
        setHasError(true);
        setErrorMessage(err instanceof Error ? err.message : "Map initialization error");
      }
    };

    // 1. Initialize once on mount or when retried
    useEffect(() => {
      const cleanup = initializeMap();
      return () => {
        cleanup?.();
      };
    }, [initCount]);

    // 2. Trigger MapLibre resize whenever 2D view becomes active
    useEffect(() => {
      if (isVisible && mapInstanceRef.current) {
        mapInstanceRef.current.resize();
        const t1 = setTimeout(() => mapInstanceRef.current?.resize(), 40);
        const t2 = setTimeout(() => mapInstanceRef.current?.resize(), 160);
        return () => {
          clearTimeout(t1);
          clearTimeout(t2);
        };
      }
    }, [isVisible]);

    // 3. Render & In-Place Reconcile Thermal Fire Markers on 2D Map (Zero DOM Thrashing)
    useEffect(() => {
      if (!mapInstanceRef.current || !isLoaded) return;
      const map = mapInstanceRef.current;
      const currentMarkerMap = markerMapRef.current;
      const incomingEventIds = new Set(events.map((e) => e.event_id));

      // A. Remove markers that no longer exist in filtered events
      for (const [id, record] of currentMarkerMap.entries()) {
        if (!incomingEventIds.has(id)) {
          record.marker.remove();
          currentMarkerMap.delete(id);
        }
      }

      // B. Reconcile existing markers in-place or create new ones
      events.forEach((event) => {
        const isSelected = selectedEvent?.event_id === event.event_id;
        const existing = currentMarkerMap.get(event.event_id);

        if (existing) {
          // In-place update selection without destroying DOM nodes
          if (existing.isSelected !== isSelected) {
            updateFireMarkerSelection(existing.element, isSelected, event);
            existing.isSelected = isSelected;
          }
          // In-place update coordinates if changed
          if (
            existing.event.latitude !== event.latitude ||
            existing.event.longitude !== event.longitude
          ) {
            existing.marker.setLngLat([event.longitude, event.latitude]);
          }
          existing.event = event;
        } else {
          // Instantiate new marker instance
          const markerEl = createFireMarkerElement({
            event,
            isSelected,
            onSelect: (evt) => onSelectEventRef.current?.(evt),
          });

          const marker = new maplibregl.Marker({ element: markerEl })
            .setLngLat([event.longitude, event.latitude])
            .addTo(map);

          currentMarkerMap.set(event.event_id, {
            marker,
            element: markerEl,
            event,
            isSelected,
          });
        }
      });
    }, [events, selectedEvent, isLoaded]);

    // 4. Smooth Camera Fly-To on Event Selection
    useEffect(() => {
      if (!mapInstanceRef.current || !selectedEvent) return;
      const map = mapInstanceRef.current;
      map.flyTo({
        center: [selectedEvent.longitude, selectedEvent.latitude],
        zoom: Math.max(map.getZoom(), 8.0),
        duration: 1000,
        essential: true,
      });
    }, [selectedEvent]);

    const handleRetry = () => {
      setInitCount((c) => c + 1);
    };

    return (
      <div className={cn("relative w-full h-full min-h-full overflow-hidden select-none bg-background", className)}>
        <div ref={containerRef} className="w-full h-full min-h-full" />

        {!isLoaded && !hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/90 backdrop-blur-sm z-10 font-mono text-xs text-foreground-muted">
            <div className="w-8 h-8 rounded-full border-2 border-accent/20 border-t-accent animate-spin mb-3" />
            <span className="tracking-wider uppercase">LOADING 2D GEOSPATIAL CARTOGRAPHY...</span>
          </div>
        )}

        {hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/95 backdrop-blur-md z-20 font-mono text-center p-6">
            <div className="w-12 h-12 rounded-panel bg-state-error/10 border border-state-error/30 flex items-center justify-center text-state-error mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-foreground tracking-wider uppercase mb-1">
              GEOSPATIAL LAYER UNAVAILABLE
            </h3>
            <p className="text-xs text-foreground-muted max-w-sm mb-4">
              {errorMessage || "Unable to load cartography tiles. Fire intelligence data remains active and accessible."}
            </p>
            <button
              onClick={handleRetry}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-surface-raised border border-border hover:border-accent text-xs font-semibold text-foreground hover:text-accent rounded-control transition-colors shadow-panel active:scale-95"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>RETRY / LOAD FALLBACK BASEMAP</span>
            </button>
          </div>
        )}

        {/* Subtle bottom-right basemap attribution */}
        <div className="absolute bottom-1 right-2 z-10 text-[9px] font-mono text-foreground-muted/60 pointer-events-none select-none">
          © CARTO © Esri © OpenStreetMap contributors
        </div>
      </div>
    );
  }
);
