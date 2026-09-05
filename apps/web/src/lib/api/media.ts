/**
 * Typed API methods for Contextual News & Media Intelligence (API-007)
 */

import { apiFetch } from "./client.ts";
import type { ContextualMediaResponse } from "../../types/media.ts";

/**
 * Fetch contextual external news coverage and video briefings for an event
 */
export async function fetchEventMedia(
  eventId: string,
  signal?: AbortSignal
): Promise<ContextualMediaResponse> {
  if (!eventId) {
    throw new Error("eventId is required to fetch contextual media");
  }
  return apiFetch<ContextualMediaResponse>(
    `/events/${encodeURIComponent(eventId)}/media`,
    {
      method: "GET",
      signal,
    }
  );
}
