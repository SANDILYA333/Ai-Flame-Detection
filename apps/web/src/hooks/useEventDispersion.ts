"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type { ThermalEvent } from "@/types/event";
import type {
  AtmosphericDispersionResult,
  PlumeHazardGeoJson,
  PasquillStabilityClass,
} from "@/types/dispersion";
import { fetchEventDispersion } from "@/lib/api/dispersion";
import { validateAndConvertDispersionToGeoJson } from "@/lib/gis/dispersion-geojson";
import { ApiClientError } from "@/lib/api/client";

export interface UseEventDispersionResult {
  dispersion: AtmosphericDispersionResult | null;
  geojson: PlumeHazardGeoJson;
  isLoading: boolean;
  isError: boolean;
  error: ApiClientError | null;
  isCalm: boolean;
  stabilityClass: PasquillStabilityClass | null;
  refetch: () => Promise<void>;
}

export function useEventDispersion(event: ThermalEvent | null | undefined): UseEventDispersionResult {
  const [dispersion, setDispersion] = useState<AtmosphericDispersionResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<ApiClientError | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const loadDispersion = useCallback(async (targetEvent: ThermalEvent) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const data = await fetchEventDispersion(
        targetEvent.event_id,
        targetEvent.latitude,
        targetEvent.longitude,
        {
          frpMw: targetEvent.frp_mw,
          signal: controller.signal,
        }
      );
      setDispersion(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      const clientError =
        err instanceof ApiClientError
          ? err
          : new ApiClientError({
              message: err instanceof Error ? err.message : "Failed to load atmospheric dispersion",
              status: 0,
              statusText: "Unknown Error",
            });
      console.warn("[WIND] Failed to fetch event dispersion:", clientError.message);
      setIsError(true);
      setError(clientError);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!event) {
      setDispersion(null);
      setIsLoading(false);
      setIsError(false);
      setError(null);
      return;
    }

    loadDispersion(event);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [event, loadDispersion]);

  const geojson = useMemo(() => {
    return validateAndConvertDispersionToGeoJson(dispersion);
  }, [dispersion]);

  const isCalm = Boolean(dispersion?.wind?.is_calm || dispersion?.dispersion?.calm_stagnation_flag);
  const stabilityClass = dispersion?.dispersion?.stability_class ?? null;

  const refetch = useCallback(async () => {
    if (event) {
      await loadDispersion(event);
    }
  }, [event, loadDispersion]);

  return {
    dispersion,
    geojson,
    isLoading,
    isError,
    error,
    isCalm,
    stabilityClass,
    refetch,
  };
}
