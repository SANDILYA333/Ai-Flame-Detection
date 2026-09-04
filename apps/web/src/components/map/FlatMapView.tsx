"use client";

import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MAPLIBRE_CONFIG } from "@/lib/map/maplibre-config";
import { ThermalEvent } from "@/types/event";
import { createFireMarkerElement, updateFireMarkerSelection } from "./FireMarkerElement";
import { useEventContext } from "@/context/EventContext";
import { fetchForestsGeoJson, ForestGeoJsonFeatureCollection } from "@/lib/api/forests";
import { DEMO_FORESTS_GEOJSON } from "@/features/forests/mock/demo-forests";
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

function computePlumeGeometries(lat: number, lon: number, frp: number, windDir = 235) {
  const downwindDeg = (windDir + 180) % 360;
  const effFrp = Math.max(5, frp);
  const plumeLenKm = Math.min(18.0, Math.max(1.5, (Math.sqrt(effFrp) * 1.1) / 3.8));
  const R = 6371;

  const offsetPoint = (distanceKm: number, bearingDeg: number): [number, number] => {
    const radLat = (lat * Math.PI) / 180;
    const radLon = (lon * Math.PI) / 180;
    const radBearing = (bearingDeg * Math.PI) / 180;
    const angDist = distanceKm / R;

    const lat2 = Math.asin(
      Math.sin(radLat) * Math.cos(angDist) +
        Math.cos(radLat) * Math.sin(angDist) * Math.cos(radBearing)
    );
    const lon2 =
      radLon +
      Math.atan2(
        Math.sin(radBearing) * Math.sin(angDist) * Math.cos(radLat),
        Math.cos(angDist) - Math.sin(radLat) * Math.sin(lat2)
      );
    return [Number(((lon2 * 180) / Math.PI).toFixed(6)), Number(((lat2 * 180) / Math.PI).toFixed(6))];
  };

  const pts: [number, number][] = [[lon, lat]];
  const halfAngle = 18;
  const steps = 6;
  for (let i = 1; i <= steps; i++) {
    const frac = i / steps;
    const d = frac * plumeLenKm;
    const b = (downwindDeg - halfAngle * (1.0 - 0.3 * frac)) % 360;
    pts.push(offsetPoint(d, b));
  }
  for (let arc = -12; arc <= 12; arc += 6) {
    const b = (downwindDeg + arc) % 360;
    pts.push(offsetPoint(plumeLenKm, b));
  }
  for (let i = steps; i >= 1; i--) {
    const frac = i / steps;
    const d = frac * plumeLenKm;
    const b = (downwindDeg + halfAngle * (1.0 - 0.3 * frac)) % 360;
    pts.push(offsetPoint(d, b));
  }
  pts.push([lon, lat]);

  const evacRadiusKm = Math.min(3.5, Math.max(0.4, 0.25 * Math.pow(effFrp, 0.35)));
  const circlePts: [number, number][] = [];
  for (let angle = 0; angle <= 360; angle += 10) {
    circlePts.push(offsetPoint(evacRadiusKm, angle));
  }

  return {
    plumeFeature: {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [pts] },
      properties: { label: "MODELLED HAZARD / DISPERSION ESTIMATE" },
    },
    evacFeature: {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [circlePts] },
      properties: { label: "ERG INITIAL ISOLATION BOUNDARY" },
    },
  };
}

function computeCircleCoordinates(lat: number, lon: number, distanceKm: number): [number, number][] {
  const R = 6371;
  const pts: [number, number][] = [];
  const radLat = (lat * Math.PI) / 180;
  const radLon = (lon * Math.PI) / 180;
  const angDist = distanceKm / R;
  for (let angle = 0; angle <= 360; angle += 10) {
    const radBearing = (angle * Math.PI) / 180;
    const lat2 = Math.asin(
      Math.sin(radLat) * Math.cos(angDist) +
        Math.cos(radLat) * Math.sin(angDist) * Math.cos(radBearing)
    );
    const lon2 =
      radLon +
      Math.atan2(
        Math.sin(radBearing) * Math.sin(angDist) * Math.cos(radLat),
        Math.cos(angDist) - Math.sin(radLat) * Math.sin(lat2)
      );
    pts.push([
      Number(((lon2 * 180) / Math.PI).toFixed(6)),
      Number(((lat2 * 180) / Math.PI).toFixed(6)),
    ]);
  }
  return pts;
}

function computeForestThreatRings(lat: number, lon: number) {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 10.0)] },
        properties: {
          level: "AWARENESS",
          label: "10 km Awareness Buffer",
          color: "#3b82f6",
        },
      },
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 5.0)] },
        properties: {
          level: "WARNING",
          label: "5 km Warning Buffer",
          color: "#f59e0b",
        },
      },
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [computeCircleCoordinates(lat, lon, 2.0)] },
        properties: {
          level: "CRITICAL",
          label: "2 km Critical Buffer",
          color: "#ef4444",
        },
      },
    ],
  };
}

/**
 * Generate 10 km Awareness & 5 km Warning monitoring circles for all monitored forests.
 */
function computeForestsMonitoringRings(forestsData: ForestGeoJsonFeatureCollection) {
  const features: any[] = [];
  if (!forestsData || !Array.isArray(forestsData.features)) {
    return { type: "FeatureCollection", features: [] };
  }

  for (const f of forestsData.features) {
    const p = f.properties || ({} as any);
    const centroidLat = p.centroid?.latitude ?? (f.geometry.type === "Polygon" ? f.geometry.coordinates[0]?.[0]?.[1] : 0);
    const centroidLon = p.centroid?.longitude ?? (f.geometry.type === "Polygon" ? f.geometry.coordinates[0]?.[0]?.[0] : 0);

    if (!centroidLat || !centroidLon) continue;

    // 10 km Awareness Circle
    features.push({
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [computeCircleCoordinates(centroidLat, centroidLon, 10.0)],
      },
      properties: {
        forest_id: p.forest_id,
        forest_name: p.name || p.name_en || "Forest Zone",
        level: "AWARENESS",
        radius_km: 10.0,
        color: "#3b82f6",
      },
    });

    // 5 km Warning Circle
    features.push({
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [computeCircleCoordinates(centroidLat, centroidLon, 5.0)],
      },
      properties: {
        forest_id: p.forest_id,
        forest_name: p.name || p.name_en || "Forest Zone",
        level: "WARNING",
        radius_km: 5.0,
        color: "#f59e0b",
      },
    });
  }

  return {
    type: "FeatureCollection",
    features,
  };
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

    // Forest State & Active Layers
    const { activeLayers } = useEventContext();
    const isForestLayerActive = activeLayers?.["indian-forest-reserves"] ?? true;
    const forestGeoJsonRef = useRef<ForestGeoJsonFeatureCollection>(DEMO_FORESTS_GEOJSON);
    const [forestData, setForestData] = useState<ForestGeoJsonFeatureCollection>(DEMO_FORESTS_GEOJSON);
    const hoverPopupRef = useRef<maplibregl.Popup | null>(null);

    const initialCameraRef = useRef({
      lat: initialLat,
      lng: initialLng,
      zoom: initialZoom,
    });

    const onCameraChangeRef = useRef(onCameraChange);
    onCameraChangeRef.current = onCameraChange;

    const onSelectEventRef = useRef(onSelectEvent);
    onSelectEventRef.current = onSelectEvent;

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
              duration: 800,
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

    /**
     * Idempotently reconciles Forest Polygons and Protection/Monitoring Radius Layers on MapLibre.
     */
    const reconcileForestLayers = useCallback((
      map: maplibregl.Map,
      data: ForestGeoJsonFeatureCollection,
      active: boolean
    ) => {
      const forestSourceId = "forest-intelligence-source";
      const forestFillLayerId = "forest-intelligence-fill";
      const forestLineLayerId = "forest-intelligence-line";
      const ringsSourceId = "forest-global-monitoring-rings-source";
      const ringsFillLayerId = "forest-global-monitoring-rings-fill";
      const ringsLineLayerId = "forest-global-monitoring-rings-line";

      if (!active) {
        if (map.getLayer(forestFillLayerId)) map.removeLayer(forestFillLayerId);
        if (map.getLayer(forestLineLayerId)) map.removeLayer(forestLineLayerId);
        if (map.getLayer(ringsFillLayerId)) map.removeLayer(ringsFillLayerId);
        if (map.getLayer(ringsLineLayerId)) map.removeLayer(ringsLineLayerId);
        if (map.getSource(forestSourceId)) map.removeSource(forestSourceId);
        if (map.getSource(ringsSourceId)) map.removeSource(ringsSourceId);
        return;
      }

      const ringsData = computeForestsMonitoringRings(data);

      // 1. Forest Protection/Monitoring Rings Source & Layers
      if (map.getSource(ringsSourceId)) {
        (map.getSource(ringsSourceId) as maplibregl.GeoJSONSource).setData(ringsData as any);
      } else {
        map.addSource(ringsSourceId, {
          type: "geojson",
          data: ringsData as any,
        });

        if (!map.getLayer(ringsFillLayerId)) {
          map.addLayer(
            {
              id: ringsFillLayerId,
              type: "fill",
              source: ringsSourceId,
              paint: {
                "fill-color": [
                  "match",
                  ["get", "level"],
                  "WARNING",
                  "#f59e0b",
                  "#3b82f6",
                ],
                "fill-opacity": [
                  "match",
                  ["get", "level"],
                  "WARNING",
                  0.04,
                  0.02,
                ],
              },
            },
            map.getLayer("selected-incident-plume-fill") ? "selected-incident-plume-fill" : undefined
          );
        }

        if (!map.getLayer(ringsLineLayerId)) {
          map.addLayer({
            id: ringsLineLayerId,
            type: "line",
            source: ringsSourceId,
            paint: {
              "line-color": [
                "match",
                ["get", "level"],
                "WARNING",
                "#f59e0b",
                "#3b82f6",
              ],
              "line-width": [
                "match",
                ["get", "level"],
                "WARNING",
                1.4,
                1.0,
              ],
              "line-dasharray": [3, 2],
              "line-opacity": 0.75,
            },
          });
        }
      }

      // 2. Forest Polygons Source & Layers
      if (map.getSource(forestSourceId)) {
        (map.getSource(forestSourceId) as maplibregl.GeoJSONSource).setData(data as any);
      } else {
        map.addSource(forestSourceId, {
          type: "geojson",
          data: data as any,
        });

        if (!map.getLayer(forestFillLayerId)) {
          map.addLayer(
            {
              id: forestFillLayerId,
              type: "fill",
              source: forestSourceId,
              paint: {
                "fill-color": [
                  "match",
                  ["get", "threat_level"],
                  "ACTIVE_FIRE",
                  "#ef4444",
                  "CRITICAL",
                  "#dc2626",
                  "WARNING",
                  "#f59e0b",
                  "AWARENESS",
                  "#3b82f6",
                  "#22c55e", // Default SAFE / Monitored Forest Green
                ],
                "fill-opacity": [
                  "match",
                  ["get", "threat_level"],
                  "ACTIVE_FIRE",
                  0.35,
                  "CRITICAL",
                  0.28,
                  "WARNING",
                  0.24,
                  "AWARENESS",
                  0.20,
                  0.18,
                ],
              },
            },
            map.getLayer("selected-incident-plume-fill") ? "selected-incident-plume-fill" : undefined
          );
        }

        if (!map.getLayer(forestLineLayerId)) {
          map.addLayer({
            id: forestLineLayerId,
            type: "line",
            source: forestSourceId,
            paint: {
              "line-color": [
                "match",
                ["get", "threat_level"],
                "ACTIVE_FIRE",
                "#b91c1c",
                "CRITICAL",
                "#991b1b",
                "WARNING",
                "#d97706",
                "AWARENESS",
                "#2563eb",
                "#16a34a",
              ],
              "line-width": 1.4,
              "line-opacity": 0.85,
            },
          });
        }

        // Add interactive hover & cursor styling for forests
        map.on("mouseenter", forestFillLayerId, (e) => {
          map.getCanvas().style.cursor = "pointer";
          const feature = e.features?.[0];
          if (!feature) return;

          const p = feature.properties as any;
          const name = p.name || p.name_en || "Monitored Forest Reserve";
          const area = p.area_km2 ? `${Math.round(p.area_km2).toLocaleString()} km²` : "N/A";
          const forestType = p.forest_type?.replace(/_/g, " ") || "Protected Woodland";
          const threat = p.threat_level || "SAFE";

          if (hoverPopupRef.current) {
            hoverPopupRef.current.remove();
          }

          hoverPopupRef.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 12,
            className: "forest-tooltip-popup",
          })
            .setLngLat(e.lngLat)
            .setHTML(`
              <div style="background:#0f172a; border:1px solid #334155; border-radius:6px; padding:8px 10px; color:#f8fafc; font-family:monospace; font-size:11px; box-shadow:0 8px 24px rgba(0,0,0,0.5);">
                <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${threat === 'ACTIVE_FIRE' ? '#ef4444' : threat === 'CRITICAL' ? '#dc2626' : threat === 'WARNING' ? '#f59e0b' : '#22c55e'};"></span>
                  <strong style="font-size:12px; color:#ffffff;">${name}</strong>
                </div>
                <div style="color:#94a3b8; font-size:10px;">${forestType} • ${p.country_code || 'GLOBAL'}</div>
                <div style="margin-top:4px; display:flex; justify-content:space-between; gap:12px;">
                  <span style="color:#cbd5e1;">Area:</span>
                  <span style="color:#38bdf8; font-weight:600;">${area}</span>
                </div>
                <div style="display:flex; justify-content:space-between; gap:12px;">
                  <span style="color:#cbd5e1;">Status:</span>
                  <span style="color:${threat === 'ACTIVE_FIRE' ? '#f87171' : threat === 'CRITICAL' ? '#f87171' : threat === 'WARNING' ? '#fbbf24' : '#4ade80'}; font-weight:bold;">${threat}</span>
                </div>
              </div>
            `)
            .addTo(map);
        });

        map.on("mouseleave", forestFillLayerId, () => {
          map.getCanvas().style.cursor = "";
          if (hoverPopupRef.current) {
            hoverPopupRef.current.remove();
            hoverPopupRef.current = null;
          }
        });
      }
    }, []);

    const initializeMap = () => {
      if (!containerRef.current) return;

      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch {}
        mapInstanceRef.current = null;
      }

      setHasError(false);
      setIsLoaded(false);

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
          reconcileForestLayers(map, forestGeoJsonRef.current, isForestLayerActive);
        };

        if (map.loaded()) {
          markLoaded();
        } else {
          map.once("load", markLoaded);
        }

        // Reconcile forest layers on any style update / reload
        map.on("styledata", () => {
          if (map.isStyleLoaded()) {
            reconcileForestLayers(map, forestGeoJsonRef.current, isForestLayerActive);
          }
        });

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
            console.warn("MapLibre style error, applying fallback:", e);
            try {
              map.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
              markLoaded();
            } catch (fallbackErr) {
              console.error("MapLibre fallback failed:", fallbackErr);
              setHasError(true);
              setErrorMessage("Unable to initialize cartography raster or vector tiles.");
            }
          }
        });

        const safetyTimer = setTimeout(() => {
          if (!map.loaded() && !fallbackAttemptedRef.current) {
            fallbackAttemptedRef.current = true;
            try {
              map.setStyle(MAPLIBRE_CONFIG.fallbackStyle as any);
              markLoaded();
            } catch (fallbackErr) {
              setHasError(true);
            }
          }
        }, 2500);

        let moveDebounceTimer: NodeJS.Timeout | null = null;
        map.on("moveend", () => {
          if (onCameraChangeRef.current) {
            const center = map.getCenter();
            const zoom = map.getZoom();
            onCameraChangeRef.current(center.lat, center.lng, zoom);
          }

          // Dynamic viewport bounding-box query for global forest loading
          if (moveDebounceTimer) clearTimeout(moveDebounceTimer);
          moveDebounceTimer = setTimeout(() => {
            const bounds = map.getBounds();
            const bbox = `${bounds.getWest().toFixed(4)},${bounds.getSouth().toFixed(4)},${bounds.getEast().toFixed(4)},${bounds.getNorth().toFixed(4)}`;
            fetchForestsGeoJson({ bbox, limit: 100 })
              .then((data) => {
                if (data && Array.isArray(data.features) && data.features.length > 0) {
                  // Merge incoming features with existing ones to avoid disappearing
                  const existingIds = new Set(forestGeoJsonRef.current.features.map((f) => f.properties.forest_id || f.id));
                  const merged = [...forestGeoJsonRef.current.features];
                  for (const f of data.features) {
                    const id = f.properties.forest_id || f.id;
                    if (!existingIds.has(id)) {
                      merged.push(f);
                      existingIds.add(id);
                    }
                  }
                  const updatedCollection = { ...forestGeoJsonRef.current, features: merged };
                  forestGeoJsonRef.current = updatedCollection;
                  setForestData(updatedCollection);
                  if (mapInstanceRef.current && mapInstanceRef.current.isStyleLoaded()) {
                    reconcileForestLayers(mapInstanceRef.current, updatedCollection, isForestLayerActive);
                  }
                }
              })
              .catch(() => {});
          }, 400);
        });

        const resizeObserver = new ResizeObserver(() => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.resize();
          }
        });

        resizeObserver.observe(containerRef.current);

        return () => {
          clearTimeout(safetyTimer);
          if (moveDebounceTimer) clearTimeout(moveDebounceTimer);
          resizeObserver.disconnect();
          if (hoverPopupRef.current) {
            hoverPopupRef.current.remove();
            hoverPopupRef.current = null;
          }
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

    useEffect(() => {
      const cleanup = initializeMap();
      return () => {
        cleanup?.();
      };
    }, [initCount]);

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

    // Initial forest load
    useEffect(() => {
      let isCancelled = false;
      fetchForestsGeoJson({ limit: 100 })
        .then((data) => {
          if (isCancelled) return;
          forestGeoJsonRef.current = data;
          setForestData(data);
          if (mapInstanceRef.current && mapInstanceRef.current.isStyleLoaded()) {
            reconcileForestLayers(mapInstanceRef.current, data, isForestLayerActive);
          }
        })
        .catch((err) => {
          console.warn("Forest initial fetch fallback used:", err);
        });
      return () => {
        isCancelled = true;
      };
    }, []);

    // Reconcile forest layer whenever activeLayers or forestData changes
    useEffect(() => {
      if (!mapInstanceRef.current || !isLoaded) return;
      const map = mapInstanceRef.current;
      if (map.isStyleLoaded()) {
        reconcileForestLayers(map, forestData, isForestLayerActive);
      }
    }, [forestData, isForestLayerActive, isLoaded, reconcileForestLayers]);

    // Render & In-Place Reconcile Thermal Fire Markers on 2D Map
    useEffect(() => {
      if (!mapInstanceRef.current || !isLoaded) return;
      const map = mapInstanceRef.current;
      const currentMarkerMap = markerMapRef.current;
      const incomingEventIds = new Set(events.map((e) => e.event_id));

      for (const [id, record] of currentMarkerMap.entries()) {
        if (!incomingEventIds.has(id)) {
          record.marker.remove();
          currentMarkerMap.delete(id);
        }
      }

      events.forEach((event) => {
        const isSelected = selectedEvent?.event_id === event.event_id;
        const existing = currentMarkerMap.get(event.event_id);

        if (existing) {
          if (existing.isSelected !== isSelected) {
            updateFireMarkerSelection(existing.element, isSelected, event);
            existing.isSelected = isSelected;
          }
          if (
            existing.event.latitude !== event.latitude ||
            existing.event.longitude !== event.longitude
          ) {
            existing.marker.setLngLat([event.longitude, event.latitude]);
          }
          existing.event = event;
        } else {
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

    // Render Gaussian Plume, Evacuation Corridor & Incident Proximity Threat Rings on Event Selection
    useEffect(() => {
      if (!mapInstanceRef.current || !isLoaded) return;
      const map = mapInstanceRef.current;

      const plumeSourceId = "selected-incident-plume-source";
      const evacSourceId = "selected-incident-evac-source";
      const forestRingsSourceId = "selected-forest-threat-rings-source";

      if (!selectedEvent) {
        if (map.getLayer("selected-incident-plume-fill")) map.removeLayer("selected-incident-plume-fill");
        if (map.getLayer("selected-incident-plume-line")) map.removeLayer("selected-incident-plume-line");
        if (map.getLayer("selected-incident-evac-fill")) map.removeLayer("selected-incident-evac-fill");
        if (map.getLayer("selected-incident-evac-line")) map.removeLayer("selected-incident-evac-line");
        if (map.getLayer("selected-forest-threat-rings-line")) map.removeLayer("selected-forest-threat-rings-line");
        if (map.getLayer("selected-forest-threat-rings-fill")) map.removeLayer("selected-forest-threat-rings-fill");
        if (map.getSource(plumeSourceId)) map.removeSource(plumeSourceId);
        if (map.getSource(evacSourceId)) map.removeSource(evacSourceId);
        if (map.getSource(forestRingsSourceId)) map.removeSource(forestRingsSourceId);
        return;
      }

      const { plumeFeature, evacFeature } = computePlumeGeometries(
        selectedEvent.latitude,
        selectedEvent.longitude,
        selectedEvent.frp_mw
      );
      const threatRingsCollection = computeForestThreatRings(
        selectedEvent.latitude,
        selectedEvent.longitude
      );

      // Proximity Threat Buffer Rings Source & Layers for selected incident
      if (map.getSource(forestRingsSourceId)) {
        (map.getSource(forestRingsSourceId) as maplibregl.GeoJSONSource).setData(threatRingsCollection as any);
      } else {
        map.addSource(forestRingsSourceId, {
          type: "geojson",
          data: threatRingsCollection as any,
        });

        if (!map.getLayer("selected-forest-threat-rings-fill")) {
          map.addLayer(
            {
              id: "selected-forest-threat-rings-fill",
              type: "fill",
              source: forestRingsSourceId,
              paint: {
                "fill-color": [
                  "match",
                  ["get", "level"],
                  "CRITICAL",
                  "#ef4444",
                  "WARNING",
                  "#f59e0b",
                  "AWARENESS",
                  "#3b82f6",
                  "#10b981",
                ],
                "fill-opacity": [
                  "match",
                  ["get", "level"],
                  "CRITICAL",
                  0.08,
                  "WARNING",
                  0.05,
                  "AWARENESS",
                  0.03,
                  0.02,
                ],
              },
            },
            map.getLayer("forest-intelligence-fill") ? "forest-intelligence-fill" : undefined
          );
        }

        if (!map.getLayer("selected-forest-threat-rings-line")) {
          map.addLayer({
            id: "selected-forest-threat-rings-line",
            type: "line",
            source: forestRingsSourceId,
            paint: {
              "line-color": [
                "match",
                ["get", "level"],
                "CRITICAL",
                "#ef4444",
                "WARNING",
                "#f59e0b",
                "AWARENESS",
                "#3b82f6",
                "#10b981",
              ],
              "line-width": [
                "match",
                ["get", "level"],
                "CRITICAL",
                1.8,
                "WARNING",
                1.4,
                "AWARENESS",
                1.0,
                1.0,
              ],
              "line-dasharray": [3, 2],
              "line-opacity": 0.85,
            },
          });
        }
      }

      // Plume Source & Layers
      if (map.getSource(plumeSourceId)) {
        (map.getSource(plumeSourceId) as maplibregl.GeoJSONSource).setData(plumeFeature as any);
      } else {
        map.addSource(plumeSourceId, {
          type: "geojson",
          data: plumeFeature as any,
        });

        if (!map.getLayer("selected-incident-plume-fill")) {
          map.addLayer({
            id: "selected-incident-plume-fill",
            type: "fill",
            source: plumeSourceId,
            paint: {
              "fill-color": "#ff9500",
              "fill-opacity": 0.25,
            },
          });
        }

        if (!map.getLayer("selected-incident-plume-line")) {
          map.addLayer({
            id: "selected-incident-plume-line",
            type: "line",
            source: plumeSourceId,
            paint: {
              "line-color": "#ff9500",
              "line-width": 1.5,
              "line-dasharray": [2, 2],
            },
          });
        }
      }

      // Evacuation Circle Source & Layers
      if (map.getSource(evacSourceId)) {
        (map.getSource(evacSourceId) as maplibregl.GeoJSONSource).setData(evacFeature as any);
      } else {
        map.addSource(evacSourceId, {
          type: "geojson",
          data: evacFeature as any,
        });

        if (!map.getLayer("selected-incident-evac-fill")) {
          map.addLayer({
            id: "selected-incident-evac-fill",
            type: "fill",
            source: evacSourceId,
            paint: {
              "fill-color": "#ff3b30",
              "fill-opacity": 0.15,
            },
          });
        }

        if (!map.getLayer("selected-incident-evac-line")) {
          map.addLayer({
            id: "selected-incident-evac-line",
            type: "line",
            source: evacSourceId,
            paint: {
              "line-color": "#ff3b30",
              "line-width": 1.5,
            },
          });
        }
      }
    }, [selectedEvent, isLoaded]);

    // Smooth Camera Fly-To on Event Selection
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
