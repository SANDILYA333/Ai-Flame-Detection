"use client";

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MAPLIBRE_CONFIG } from "@/lib/map/maplibre-config";
import { ThermalEvent } from "@/types/event";
import { createFireMarkerElement } from "./FireMarkerElement";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export interface FlatMapViewProps {
  initialLat?: number;
  initialLng?: number;
  initialZoom?: number;
  events?: ThermalEvent[];
  selectedEvent?: ThermalEvent | null;
  onSelectEvent?: (event: ThermalEvent) => void;
  onCameraChange?: (lat: number, lng: number, zoom: number) => void;
  className?: string;
}

export interface FlatMapViewHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
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
      onSelectEvent,
      onCameraChange,
      className,
    }: FlatMapViewProps,
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<maplibregl.Map | null>(null);
    const markersRef = useRef<maplibregl.Marker[]>([]);
    const [isLoaded, setIsLoaded] = useState(false);
    const [hasError, setHasError] = useState(false);

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
        getMapInstance: () => mapInstanceRef.current,
      }),
      []
    );

    // 1. Initialize MapLibre GL Map Once on Mount
    useEffect(() => {
      if (!containerRef.current || mapInstanceRef.current) return;

      try {
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

        // Fallback safety: ensure loading screen clears within 500ms
        const fallbackTimer = setTimeout(() => {
          setIsLoaded(true);
          map.resize();
        }, 500);

        // Handle style load failures with fallback to ESRI Dark Canvas
        map.on("error", (e) => {
          if (e && (e as any).status === 404) {
            try {
              map.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
            } catch (fallbackErr) {
              console.warn("Failed to set fallback style:", fallbackErr);
              setHasError(true);
            }
          }
        });

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
          clearTimeout(fallbackTimer);
          resizeObserver.disconnect();
          markersRef.current.forEach((m) => m.remove());
          markersRef.current = [];
          if (mapInstanceRef.current) {
            mapInstanceRef.current.remove();
            mapInstanceRef.current = null;
          }
        };
      } catch (err) {
        console.error("Failed to initialize MapLibre GL:", err);
        setIsLoaded(true);
        setHasError(true);
      }
    }, []);

    // 2. Render & Update Thermal Fire Markers on 2D Map
    useEffect(() => {
      if (!mapInstanceRef.current || !isLoaded) return;
      const map = mapInstanceRef.current;

      // Clear existing markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      // Create fresh markers
      events.forEach((event) => {
        const isSelected = selectedEvent?.event_id === event.event_id;
        const markerEl = createFireMarkerElement({
          event,
          isSelected,
          onSelect: (evt) => onSelectEventRef.current?.(evt),
        });

        const marker = new maplibregl.Marker({ element: markerEl })
          .setLngLat([event.longitude, event.latitude])
          .addTo(map);

        markersRef.current.push(marker);
      });
    }, [events, selectedEvent, isLoaded]);

    // 3. Smooth Camera Fly-To on Event Selection
    useEffect(() => {
      if (!mapInstanceRef.current || !selectedEvent) return;
      const map = mapInstanceRef.current;
      map.flyTo({
        center: [selectedEvent.longitude, selectedEvent.latitude],
        zoom: Math.max(map.getZoom(), 8.0),
        duration: 1200,
        essential: true,
      });
    }, [selectedEvent]);

    return (
      <div className={cn("relative w-full h-full overflow-hidden select-none", className)}>
        <div ref={containerRef} className="w-full h-full" />

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
              Unable to load vector cartography tiles. Fire intelligence data remains active and accessible.
            </p>
            <button
              onClick={() => {
                if (mapInstanceRef.current) {
                  mapInstanceRef.current.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
                  setHasError(false);
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border hover:border-accent text-xs text-foreground-secondary hover:text-foreground rounded-control transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>LOAD FALLBACK BASEMAP</span>
            </button>
          </div>
        )}

        {/* Subtle bottom-right basemap attribution */}
        <div className="absolute bottom-1 right-2 z-10 text-[9px] font-mono text-foreground-muted/60 pointer-events-none select-none">
          © OpenFreeMap © OpenStreetMap
        </div>
      </div>
    );
  }
);
