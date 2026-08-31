"use client";

import { useState, useCallback } from "react";
import { ViewMode } from "@/components/map/ViewModeToggle";
import { APP_CONFIG } from "@/config/ui";

export interface MapCameraState {
  lat: number;
  lng: number;
  zoom: number;
}

export function useMapMode(initialMode: ViewMode = "3D") {
  const [viewMode, setViewMode] = useState<ViewMode>(initialMode);
  const [camera, setCamera] = useState<MapCameraState>({
    lat: APP_CONFIG.defaultCenter.lat,
    lng: APP_CONFIG.defaultCenter.lon,
    zoom: APP_CONFIG.defaultCenter.zoom,
  });

  const updateCamera = useCallback((newCamera: Partial<MapCameraState>) => {
    setCamera((prev) => ({ ...prev, ...newCamera }));
  }, []);

  const resetCamera = useCallback(() => {
    setCamera({
      lat: APP_CONFIG.defaultCenter.lat,
      lng: APP_CONFIG.defaultCenter.lon,
      zoom: APP_CONFIG.defaultCenter.zoom,
    });
  }, []);

  return {
    viewMode,
    setViewMode,
    camera,
    updateCamera,
    resetCamera,
  };
}
