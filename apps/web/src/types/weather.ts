/**
 * Canonical TypeScript types for Weather & Wind Intelligence (Phase 1 & 2).
 */

export type DataStatus = "LIVE" | "CACHED" | "UNAVAILABLE";
export type DataQuality = "LIVE" | "CACHED" | "FALLBACK" | "UNAVAILABLE";
export type WindState = "CALM" | "LIGHT" | "MODERATE" | "FRESH" | "STRONG" | "GALE";

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface WindVector {
  speed_ms: number;
  direction_from_deg: number;
  direction_from_label: string;
  direction_to_deg: number;
  downwind_direction_label: string;
  gust_ms: number | null;
  u_ms: number;
  v_ms: number;
  is_calm: boolean;
  wind_state: WindState;
}

export interface AtmosphereData {
  temperature_c: number;
  relative_humidity_pct: number;
  surface_pressure_hpa: number | null;
  precipitation_mm: number | null;
  cloud_cover_pct: number | null;
  boundary_layer_height_m: number | null;
  soil_moisture_m3_m3: number | null;
}

export interface WeatherForecastPoint {
  forecast_time: string;
  horizon_hours: number;
  atmosphere: AtmosphereData;
  wind: WindVector;
}

export interface WeatherProviderInfo {
  name: string;
  model?: string | null;
}

export interface WeatherResponse {
  location: Coordinate;
  observed_at: string;
  retrieved_at: string;
  data_status: DataStatus;
  data_quality: DataQuality;
  atmosphere: AtmosphereData;
  wind: WindVector;
  forecast: WeatherForecastPoint[];
  provider: WeatherProviderInfo;
}

export interface EventWeatherResponse {
  event_id: string;
  weather: WeatherResponse;
  enriched_at: string;
}
