/**
 * Standard API envelope & health types
 */

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
  };
  meta?: {
    timestamp_utc: string;
    duration_ms: number;
  };
}

export interface SystemStatus {
  service: string;
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  firms_stream_ready: boolean;
  model_ready: boolean;
  active_events: number;
}
