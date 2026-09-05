"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback, useImperativeHandle, forwardRef } from "react";
import Globe, { GlobeInstance } from "globe.gl";
import { GLOBE_CONFIG } from "@/lib/map/globe-config";
import { ThermalEvent } from "@/types/event";
import { createFireMarkerElement, updateFireMarkerSelection } from "./FireMarkerElement";
import { WebGLFallback } from "./WebGLFallback";
import { useEventContext } from "@/context/EventContext";
import { fetchForestsGeoJson, ForestGeoJsonFeatureCollection } from "@/lib/api/forests";
import { DEMO_FORESTS_GEOJSON } from "@/features/forests/mock/demo-forests";
import { normalizeGlobePolygonGeometry, isGlobePolygonValid } from "@/lib/map/globe-geometry";
import { useIndustrialAssets } from "@/hooks/useIndustrialAssets";
import { isIndustrialAssetVisible } from "@/lib/api/industrial";
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
    const globeElementCacheRef = useRef<Map<string, HTMLElement>>(new Map());
    const [hasWebGL, setHasWebGL] = useState<boolean | null>(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const autoRotateTimerRef = useRef<NodeJS.Timeout | null>(null);
    const isInteractingRef = useRef<boolean>(false);
    const renderIndustrialPointsRef = useRef<(() => void) | null>(null);

    const { activeLayers } = useEventContext();
    const isForestLayerActive = activeLayers?.["indian-forest-reserves"] ?? true;
    const [forestData, setForestData] = useState<ForestGeoJsonFeatureCollection>(DEMO_FORESTS_GEOJSON);

    // Normalize forest polygon geometries for 3D spherical rendering (prevents whole-earth green coverage)
    const normalizedForestFeatures = useMemo(() => {
      if (!isForestLayerActive || !forestData?.features?.length) return [];
      return forestData.features
        .filter((f) => f && isGlobePolygonValid(f.geometry))
        .map((f) => ({
          ...f,
          geometry: normalizeGlobePolygonGeometry(f.geometry),
        }));
    }, [forestData, isForestLayerActive]);

    // Industrial Infrastructure Layer State & Dynamic GIS Layer Selection
    const { data: industrialData } = useIndustrialAssets();
    const filteredIndustrialFeatures = useMemo(() => {
      if (!industrialData?.features?.length) return [];
      return industrialData.features.filter((f) =>
        isIndustrialAssetVisible(f, activeLayers)
      );
    }, [industrialData, activeLayers]);

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

    // Initial forest load for 3D globe
    useEffect(() => {
      fetchForestsGeoJson({ limit: 100 })
        .then((data) => {
          if (data && Array.isArray(data.features)) {
            setForestData(data);
          }
        })
        .catch(() => {});
    }, []);

    // 1. Initialize Globe Instance Once on Mount
    useEffect(() => {
      try {
        const canvas = document.createElement("canvas");
        const gl =
          canvas.getContext("webgl2") ||
          canvas.getContext("webgl") ||
          canvas.getContext("experimental-webgl");
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
              if (controls) controls.autoRotate = true;
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
          container.addEventListener(
            "wheel",
            () => {
              handleUserInteractionStart();
              handleUserInteractionEnd();
            },
            { passive: true }
          );
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

        const elementCache = globeElementCacheRef.current;

        return () => {
          resizeObserver.disconnect();
          if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
          elementCache.clear();
          if (globeInstanceRef.current) {
            try {
              const g = globeInstanceRef.current as any;
              if (typeof g._destructor === "function") {
                g._destructor();
              }
              if (typeof g.pauseAnimation === "function") {
                g.pauseAnimation();
              }
              const renderer = g.renderer?.();
              if (renderer) {
                renderer.dispose();
              }
            } catch (cleanupErr) {
              console.warn("Globe cleanup warning:", cleanupErr);
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

    // 2. Pause / Resume Auto-Rotation and Resize based on Visibility
    useEffect(() => {
      if (!globeInstanceRef.current) return;
      const controls = globeInstanceRef.current.controls();
      if (controls) {
        controls.autoRotate = isVisible;
      }
      if (isVisible && containerRef.current) {
        const w = containerRef.current.clientWidth;
        const h = containerRef.current.clientHeight;
        if (w > 0 && h > 0) {
          globeInstanceRef.current.width(w).height(h);
        }
        renderIndustrialPointsRef.current?.();
      }
    }, [isVisible]);

    // 3. Render Thermal Fire Markers & Radiating Rings with In-Place Element Caching
    useEffect(() => {
      if (!globeInstanceRef.current || !isLoaded) return;
      const globe = globeInstanceRef.current as any;
      const cache = globeElementCacheRef.current;
      const activeIds = new Set(events.map((e) => e.event_id));

      // Clean up cached elements that are no longer active
      for (const id of cache.keys()) {
        if (!activeIds.has(id)) {
          cache.delete(id);
        }
      }

      globe
        .htmlElementsData(events)
        .htmlLat((d: any) => d.latitude)
        .htmlLng((d: any) => d.longitude)
        .htmlElement((d: any) => {
          const isSelected = selectedEvent?.event_id === d.event_id;
          const cached = cache.get(d.event_id);
          if (cached) {
            updateFireMarkerSelection(cached, isSelected, d as ThermalEvent);
            return cached;
          }
          const el = createFireMarkerElement({
            event: d as ThermalEvent,
            isSelected,
            onSelect: (evt) => onSelectEventRef.current?.(evt),
          });
          cache.set(d.event_id, el);
          return el;
        });

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

    // 4. Render 3D Forest Polygons on Globe
    useEffect(() => {
      if (!globeInstanceRef.current || !isLoaded) return;
      const globe = globeInstanceRef.current as any;

      if (!isForestLayerActive || !normalizedForestFeatures.length) {
        globe.polygonsData([]);
        return;
      }

      globe
        .polygonsData(normalizedForestFeatures)
        .polygonGeoJsonGeometry((d: any) => d.geometry)
        .polygonCapColor((d: any) => {
          const lvl = d.properties?.threat_level;
          if (lvl === "ACTIVE_FIRE") return "rgba(239, 68, 68, 0.55)";
          if (lvl === "CRITICAL") return "rgba(220, 38, 38, 0.45)";
          if (lvl === "WARNING") return "rgba(245, 158, 11, 0.40)";
          return "rgba(34, 197, 94, 0.35)";
        })
        .polygonSideColor(() => "rgba(22, 163, 74, 0.15)")
        .polygonStrokeColor((d: any) => {
          const lvl = d.properties?.threat_level;
          if (lvl === "ACTIVE_FIRE") return "#ef4444";
          if (lvl === "CRITICAL") return "#dc2626";
          if (lvl === "WARNING") return "#f59e0b";
          return "#16a34a";
        })
        .polygonAltitude(0.008)
        .polygonLabel(
          (d: any) => `
          <div style="background:#0f172a; border:1px solid #334155; padding:6px 10px; border-radius:4px; font-family:monospace; font-size:11px; color:#f8fafc;">
            <strong>${d.properties?.name || d.properties?.name_en || "Monitored Forest"}</strong><br/>
            <span style="color:#94a3b8;">${d.properties?.forest_type || "Forest"} • ${d.properties?.country_code || "GLOBAL"}</span>
          </div>
        `
        );
    }, [normalizedForestFeatures, isForestLayerActive, isLoaded]);

    // 4b. Render 3D Industrial Infrastructure Points on Globe
    const renderIndustrialPoints = useCallback(() => {
      if (!globeInstanceRef.current || !isLoaded) return;
      const globe = globeInstanceRef.current as any;

      if (!filteredIndustrialFeatures.length) {
        globe.pointsTransitionDuration(0);
        globe.pointsData([]);
        return;
      }

      globe
        .pointsTransitionDuration(0)
        .pointsData([...filteredIndustrialFeatures])
        .pointLat((d: any) => d.geometry.coordinates[1])
        .pointLng((d: any) => d.geometry.coordinates[0])
        .pointColor((d: any) => {
          const ind = d.properties?.industry;
          if (ind === "power") return "#eab308";
          if (ind === "oil_gas") return "#f97316";
          if (ind === "metallurgy") return "#a855f7";
          if (ind === "chemical") return "#06b6d4";
          return "#10b981";
        })
        .pointAltitude(0.005)
        .pointRadius(0.22)
        .pointLabel((d: any) => {
          const p = d.properties || {};
          const ind = String(p.industry || "industrial").toUpperCase();
          const status = String(p.status || "operating").toUpperCase();
          const cap = p.capacity ? ` • ${p.capacity} ${p.capacity_unit || "MW"}` : "";
          const loc = [p.city, p.state, p.country || "India"].filter(Boolean).join(", ");
          const sectorColor =
            p.industry === "power"
              ? "#eab308"
              : p.industry === "oil_gas"
              ? "#f97316"
              : p.industry === "metallurgy"
              ? "#a855f7"
              : p.industry === "chemical"
              ? "#06b6d4"
              : "#10b981";

          return `
            <div style="font-family: ui-monospace, monospace; font-size: 11px; padding: 6px 9px; background: rgba(13, 17, 23, 0.95); border: 1px solid #252c35; border-radius: 5px; color: #f2f5f7; pointer-events: none; box-shadow: 0 6px 18px rgba(0,0,0,0.6); max-width: 240px;">
              <div style="font-weight: bold; color: #f2f5f7; margin-bottom: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${p.name || "Industrial Facility"}</div>
              <div style="display: flex; gap: 4px; margin-bottom: 3px; font-size: 9px;">
                <span style="background: ${sectorColor}26; color: ${sectorColor}; padding: 1px 4px; border-radius: 2px; border: 1px solid ${sectorColor}55; font-weight: 600;">${ind}</span>
                <span style="background: rgba(57, 255, 136, 0.15); color: #39ff88; padding: 1px 4px; border-radius: 2px; border: 1px solid rgba(57, 255, 136, 0.3); font-weight: 600;">${status}</span>
              </div>
              ${loc ? `<div style="color: #b5bec8; font-size: 10px;">📍 ${loc}</div>` : ""}
              ${cap ? `<div style="color: #ffbf24; font-size: 10px; font-weight: 600;">⚡ ${cap.replace(/^ • /, "")}</div>` : ""}
            </div>
          `;
        });
    }, [filteredIndustrialFeatures, isLoaded]);

    useEffect(() => {
      renderIndustrialPointsRef.current = renderIndustrialPoints;
      renderIndustrialPoints();
    }, [renderIndustrialPoints]);

    // 5. Smooth Camera Fly-To on Event Selection
    useEffect(() => {
      if (!globeInstanceRef.current || !selectedEvent) return;
      const globe = globeInstanceRef.current;
      globe.pointOfView(
        {
          lat: selectedEvent.latitude,
          lng: selectedEvent.longitude,
          altitude: 1.4,
        },
        1000
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
