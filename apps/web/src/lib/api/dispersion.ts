/**
 * Atmospheric Dispersion & Downwind Hazard Intelligence API client for SIH26162 (Phase 3 & 4).
 */

import { apiFetch } from "./client";
import type {
  AtmosphereData,
  Coordinate,
  DataQuality,
  WindVector,
} from "@/types/weather";
import type {
  AtmosphericDispersionResult,
  DispersionCalculationResponse,
  DispersionSamplePoint,
  DispersionSummary,
  PasquillStabilityClass,
} from "@/types/dispersion";

export type {
  AtmosphericDispersionResult,
  DispersionCalculationResponse,
  DispersionSamplePoint,
  DispersionSummary,
  PasquillStabilityClass,
};

export interface FetchDispersionOptions {
  frpMw?: number;
  releaseHeightM?: number;
  customWindSpeedMs?: number;
  customWindDirectionDeg?: number;
  isDaytime?: boolean;
  maxDistanceKm?: number;
  signal?: AbortSignal;
}

export interface DispersionCalculationRequestBody {
  latitude: number;
  longitude: number;
  frp_mw?: number | null;
  release_height_m?: number | null;
  custom_wind_speed_ms?: number | null;
  custom_wind_direction_deg?: number | null;
  is_daytime?: boolean | null;
  max_distance_km?: number | null;
}

/**
 * Fetch atmospheric dispersion hazard profile using GET query parameters.
 */
export async function fetchDispersion(
  latitude: number,
  longitude: number,
  options: FetchDispersionOptions = {}
): Promise<DispersionCalculationResponse> {
  const {
    frpMw,
    releaseHeightM,
    customWindSpeedMs,
    customWindDirectionDeg,
    isDaytime,
    maxDistanceKm,
    signal,
  } = options;

  return apiFetch<DispersionCalculationResponse>("/dispersion", {
    params: {
      latitude,
      longitude,
      frp_mw: frpMw,
      release_height_m: releaseHeightM,
      custom_wind_speed_ms: customWindSpeedMs,
      custom_wind_direction_deg: customWindDirectionDeg,
      is_daytime: isDaytime,
      max_distance_km: maxDistanceKm,
    },
    signal,
  });
}

/**
 * Calculate atmospheric dispersion via POST body with explicit parameters.
 */
export async function calculateDispersion(
  body: DispersionCalculationRequestBody,
  signal?: AbortSignal
): Promise<DispersionCalculationResponse> {
  return apiFetch<DispersionCalculationResponse>("/dispersion", {
    method: "POST",
    body: JSON.stringify(body),
    headers: {
      "Content-Type": "application/json",
    },
    signal,
  });
}

/**
 * Fetch atmospheric dispersion hazard profile coupled to a specific thermal event.
 */
export async function fetchEventDispersion(
  eventId: string,
  latitude: number,
  longitude: number,
  options: FetchDispersionOptions = {}
): Promise<DispersionCalculationResponse> {
  const { frpMw, releaseHeightM, maxDistanceKm, signal } = options;

  return apiFetch<DispersionCalculationResponse>(
    `/dispersion/events/${encodeURIComponent(eventId)}`,
    {
      params: {
        latitude,
        longitude,
        frp_mw: frpMw,
        release_height_m: releaseHeightM,
        max_distance_km: maxDistanceKm,
      },
      signal,
    }
  );
}
