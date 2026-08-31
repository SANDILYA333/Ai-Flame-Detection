"use client";

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";
import Globe, { GlobeInstance } from "globe.gl";
import { GLOBE_CONFIG } from "@/lib/map/globe-config";
import { ThermalEvent } from "@/types/event";
import { createFireMarkerElement } from "./FireMarkerElement";
import { WebGLFallback } from "./WebGLFallback";
import { cn } from "@/lib/utils";

export interface GlobeViewProps {
  initialLat?: number;
  initialLng?: number;
  events?: ThermalEvent[];
  selectedEvent?: ThermalEvent | null;
  isVisible?: boolean;
  onSelectEvent?: (event: ThermalEvent) => void;
  onCameraChange?: (lat: number, lng: number, altitude: number) => void;
  onSwitchTo2D?: () => void;
  className?: string;
}

export interface GlobeViewHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
  getGlobeInstance: () => GlobeInstance | null;
}

export const GlobeView = forwardRef<GlobeViewHandle, GlobeViewProps>(
  function GlobeView(
    {
      initialLat = GLOBE_CONFIG.initialCamera.lat,
      initialLng = GLOBE_CONFIG.initialCamera.lng,
      events = [],
      selectedEvent,
      isVisible = true,
      onSelectEvent,
      onCameraChange,
      onSwitchTo2D,
      className,
    }: GlobeViewProps,
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const globeInstanceRef = useRef<GlobeInstance | null>(null);
    const [hasWebGL, setHasWebGL] = useState<boolean | null>(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const autoRotateTimerRef = useRef<NodeJS.Timeout | null>(null);
    const isInteractingRef = useRef<boolean>(false);

    const initialCameraRef = useRef({
      lat: initialLat,
      lng: initialLng,
    });

    // Stable callback refs to prevent effect recreation
    const onCameraChangeRef = useRef(onCameraChange);
    onCameraChangeRef.current = onCameraChange;

    const onSelectEventRef = useRef(onSelectEvent);
    onSelectEventRef.current = onSelectEvent;

    // Expose imperative navigation handles
    useImperativeHandle(
      ref,
      () => ({
        zoomIn: () => {
          if (globeInstanceRef.current) {
            const pov = globeInstanceRef.current.pointOfView();
            globeInstanceRef.current.pointOfView(
              { ...pov, altitude: Math.max(0.4, pov.altitude * 0.75) },
              400
            );
          }
        },
        zoomOut: () => {
          if (globeInstanceRef.current) {
            const pov = globeInstanceRef.current.pointOfView();
            globeInstanceRef.current.pointOfView(
              { ...pov, altitude: Math.min(3.8, pov.altitude * 1.35) },
              400
            );
          }
        },
        resetView: () => {
          if (globeInstanceRef.current) {
            globeInstanceRef.current.pointOfView(
              {
                lat: initialCameraRef.current.lat,
                lng: initialCameraRef.current.lng,
                altitude: GLOBE_CONFIG.initialCamera.altitude,
              },
              1000
            );
          }
        },
        getGlobeInstance: () => globeInstanceRef.current,
      }),
      []
    );

    // 1. Initialize Globe Instance Once on Mount
    useEffect(() => {
      try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (!gl) {
          setHasWebGL(false);
          return;
        }
        setHasWebGL(true);
      } catch {
        setHasWebGL(false);
        return;
      }

      if (!containerRef.current || globeInstanceRef.current) return;

      const container = containerRef.current;
      const width = container.clientWidth || window.innerWidth;
      const height = container.clientHeight || window.innerHeight;

      try {
        const globe = new (Globe as any)(container)
          .width(width)
          .height(height)
          .backgroundColor(GLOBE_CONFIG.colors.ocean)
          .globeImageUrl(GLOBE_CONFIG.textures.globeNight)
          .bumpImageUrl(GLOBE_CONFIG.textures.bumpMap)
          .showAtmosphere(GLOBE_CONFIG.atmosphere.show)
          .atmosphereColor(GLOBE_CONFIG.atmosphere.color)
          .atmosphereAltitude(GLOBE_CONFIG.atmosphere.altitude)
          .pointOfView(
            {
              lat: initialCameraRef.current.lat,
              lng: initialCameraRef.current.lng,
              altitude: GLOBE_CONFIG.initialCamera.altitude,
            },
            800
          );

        globeInstanceRef.current = globe;

        // Configure Orbit Controls & Auto-Rotation
        const controls = globe.controls();
        if (controls) {
          controls.autoRotate = true;
          controls.autoRotateSpeed = GLOBE_CONFIG.controls.autoRotateSpeed;
          controls.enableDamping = true;
          controls.dampingFactor = GLOBE_CONFIG.controls.dampingFactor;
          controls.minDistance = 120;
          controls.maxDistance = 480;

          const handleUserInteractionStart = () => {
            isInteractingRef.current = true;
            controls.autoRotate = false;
            if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
            autoRotateTimerRef.current = setTimeout(() => {
              isInteractingRef.current = false;
              controls.autoRotate = true;
            }, GLOBE_CONFIG.controls.autoRotateResumeDelay);
          };

          const handleUserInteractionEnd = () => {
            if (onCameraChangeRef.current && globeInstanceRef.current) {
              const pov = globeInstanceRef.current.pointOfView();
              onCameraChangeRef.current(pov.lat, pov.lng, pov.altitude);
            }
          };

          container.addEventListener("pointerdown", handleUserInteractionStart);
          container.addEventListener("pointerup", handleUserInteractionEnd);
          container.addEventListener("wheel", () => {
            handleUserInteractionStart();
            handleUserInteractionEnd();
          }, { passive: true });
          container.addEventListener("touchstart", handleUserInteractionStart, { passive: true });
          container.addEventListener("touchend", handleUserInteractionEnd, { passive: true });

          // Only propagate camera change when user is actively moving the camera
          controls.addEventListener("change", () => {
            if (isInteractingRef.current && onCameraChangeRef.current && globeInstanceRef.current) {
              const pov = globeInstanceRef.current.pointOfView();
              onCameraChangeRef.current(pov.lat, pov.lng, pov.altitude);
            }
          });
        }

        setIsLoaded(true);

        const resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            const { width: newWidth, height: newHeight } = entry.contentRect;
            if (newWidth > 0 && newHeight > 0 && globeInstanceRef.current) {
              globeInstanceRef.current.width(newWidth).height(newHeight);
            }
          }
        });

        resizeObserver.observe(container);

        return () => {
          resizeObserver.disconnect();
          if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
          if (globeInstanceRef.current) {
            const renderer = globeInstanceRef.current.renderer?.();
            if (renderer) {
              renderer.dispose();
              renderer.forceContextLoss();
            }
            if (container) {
              container.innerHTML = "";
            }
            globeInstanceRef.current = null;
          }
        };
      } catch (err) {
        console.error("Failed to initialize 3D Globe:", err);
        setHasWebGL(false);
      }
    }, []);

    // 2. Render Thermal Fire Markers & Radiating Rings
    useEffect(() => {
      if (!globeInstanceRef.current || !isLoaded) return;
      const globe = globeInstanceRef.current as any;

      globe
        .htmlElementsData(events)
        .htmlLat((d: any) => d.latitude)
        .htmlLng((d: any) => d.longitude)
        .htmlElement((d: any) =>
          createFireMarkerElement({
            event: d as ThermalEvent,
            isSelected: selectedEvent?.event_id === d.event_id,
            onSelect: (evt) => onSelectEventRef.current?.(evt),
          })
        );

      const severeEvents = events.filter((e) => e.frp_mw > 100);
      globe
        .ringsData(severeEvents)
        .ringLat((d: any) => d.latitude)
        .ringLng((d: any) => d.longitude)
        .ringAltitude(0.015)
        .ringColor((d: any) => (t: number) => {
          const alpha = Math.max(0, (1 - t) * 0.7);
          return d.classification === "INDUSTRIAL"
            ? `rgba(255, 106, 0, ${alpha})`
            : `rgba(255, 191, 36, ${alpha})`;
        })
        .ringMaxRadius(2.5)
        .ringPropagationSpeed(1.8)
        .ringRepeatPeriod(2400);
    }, [events, selectedEvent, isLoaded]);

    // 3. Smooth Camera Fly-To on Event Selection
    useEffect(() => {
      if (!globeInstanceRef.current || !selectedEvent) return;
      const globe = globeInstanceRef.current;
      globe.pointOfView(
        {
          lat: selectedEvent.latitude,
          lng: selectedEvent.longitude,
          altitude: 1.4,
        },
        1200
      );
    }, [selectedEvent]);

    if (hasWebGL === false) {
      return (
        <div className="w-full h-full flex items-center justify-center">
          <WebGLFallback onSwitchTo2D={onSwitchTo2D} />
        </div>
      );
    }

    return (
      <div className={cn("relative w-full h-full overflow-hidden select-none", className)}>
        <div ref={containerRef} className="w-full h-full" />

        {!isLoaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/90 backdrop-blur-sm z-10 font-mono text-xs text-foreground-muted">
            <div className="w-8 h-8 rounded-full border-2 border-accent/20 border-t-accent animate-spin mb-3" />
            <span className="tracking-wider uppercase">INITIALIZING 3D ORBITAL ENGINE...</span>
          </div>
        )}
      </div>
    );
  }
);
