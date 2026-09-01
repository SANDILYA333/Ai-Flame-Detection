/**
 * Typed API methods for canonical thermal events
 */

import { apiFetch } from "./client.ts";
import type {
  EventsQueryParams,
  EventsResponse,
  EventDetailResponse,
  EventTimelineResponse,
  EventEvidenceResponse,
} from "@/types/event";
import type { IntelligenceResult } from "@/types/intelligence";

/**
 * Fetch a paginated list of canonical thermal events matching optional query filters
 */
export async function fetchEvents(
  params: EventsQueryParams = {},
  signal?: AbortSignal
): Promise<EventsResponse> {
  return apiFetch<EventsResponse>("/events", {
    method: "GET",
    params: {
      min_lat: params.min_lat,
      max_lat: params.max_lat,
      min_lon: params.min_lon,
      max_lon: params.max_lon,
      start_time: params.start_time,
      end_time: params.end_time,
      status: params.status,
      classification_state: params.classification_state,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    },
    signal,
  });
}

/**
 * Fetch full canonical detail for a specific thermal event
 */
export async function fetchEventDetail(
  eventId: string,
  signal?: AbortSignal
): Promise<EventDetailResponse> {
  if (!eventId) {
    throw new Error("eventId is required to fetch event detail");
  }
  return apiFetch<EventDetailResponse>(`/events/${encodeURIComponent(eventId)}`, {
    method: "GET",
    signal,
  });
}

/**
 * Fetch chronological detection timeline for an event episode
 */
export async function fetchEventTimeline(
  eventId: string,
  signal?: AbortSignal
): Promise<EventTimelineResponse> {
  if (!eventId) {
    throw new Error("eventId is required to fetch event timeline");
  }
  return apiFetch<EventTimelineResponse>(
    `/events/${encodeURIComponent(eventId)}/timeline`,
    {
      method: "GET",
      signal,
    }
  );
}

/**
 * Fetch contextual and scientific reference evidence linked to an event
 */
export async function fetchEventEvidence(
  eventId: string,
  signal?: AbortSignal
): Promise<EventEvidenceResponse> {
  if (!eventId) {
    throw new Error("eventId is required to fetch event evidence");
  }
  return apiFetch<EventEvidenceResponse>(
    `/events/${encodeURIComponent(eventId)}/evidence`,
    {
      method: "GET",
      signal,
    }
  );
}

/**
 * Fetch calibrated intelligence inference result for an event
 */
export async function fetchEventIntelligence(
  eventId: string,
  signal?: AbortSignal
): Promise<IntelligenceResult> {
  if (!eventId) {
    throw new Error("eventId is required to fetch event intelligence");
  }
  return apiFetch<IntelligenceResult>(
    `/events/${encodeURIComponent(eventId)}/intelligence`,
    {
      method: "GET",
      signal,
    }
  );
}
