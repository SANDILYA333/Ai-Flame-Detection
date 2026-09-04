/**
 * Weather & Wind Intelligence API client for SIH26162 (Phase 1 & 2).
 */

import { apiFetch } from "./client";
import type {
  AtmosphereData,
  Coordinate,
  DataQuality,
  DataStatus,
  EventWeatherResponse,
  WeatherForecastPoint,
  WeatherProviderInfo,
  WeatherResponse,
  WindState,
  WindVector,
} from "@/types/weather";

export type {
  AtmosphereData,
  Coordinate,
  DataQuality,
  DataStatus,
  EventWeatherResponse,
  WeatherForecastPoint,
  WeatherProviderInfo,
  WeatherResponse,
  WindState,
  WindVector,
};

export interface FetchWeatherOptions {
  forecastHours?: number;
  allowCached?: boolean;
  signal?: AbortSignal;
}

/**
 * Fetch meteorological observations and decomposed wind vector for geographic coordinates.
 */
export async function fetchWeather(
  latitude: number,
  longitude: number,
  options: FetchWeatherOptions = {}
): Promise<WeatherResponse> {
  const { forecastHours = 24, allowCached = true, signal } = options;

  return apiFetch<WeatherResponse>("/weather", {
    params: {
      latitude,
      longitude,
      forecast_hours: forecastHours,
      allow_cached: allowCached,
    },
    signal,
  });
}

/**
 * Fetch meteorological observations enriched for a specific thermal event.
 */
export async function fetchEventWeather(
  eventId: string,
  latitude: number,
  longitude: number,
  options: FetchWeatherOptions = {}
): Promise<EventWeatherResponse> {
  const { forecastHours = 24, signal } = options;

  return apiFetch<EventWeatherResponse>(`/weather/events/${encodeURIComponent(eventId)}`, {
    params: {
      latitude,
      longitude,
      forecast_hours: forecastHours,
    },
    signal,
  });
}
