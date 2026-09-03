import type {
  EventResponseRecommendation,
  NotificationRequest,
  NotificationResponse,
  ResponseActivityRecord,
} from "../../types/responders.ts";
import type { ThermalEvent } from "../../types/event.ts";
import { calculateLocalResponseRecommendation } from "./engine.ts";

const API_BASE_URL =
  typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000";

// In-memory frontend session activity store for offline demo persistence
const localSessionActivity: ResponseActivityRecord[] = [];

/**
 * Fetches prioritized emergency responder recommendations from FastAPI backend
 * or seamlessly falls back to the deterministic local engine.
 */
export async function fetchEventResponders(
  event: ThermalEvent
): Promise<EventResponseRecommendation> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/events/${encodeURIComponent(event.event_id)}/responders`,
      {
        headers: { Accept: "application/json" },
      }
    );

    if (res.ok) {
      const data = await res.json();
      return data as EventResponseRecommendation;
    }
  } catch {
    // Network or server error -> fallback locally
  }

  return calculateLocalResponseRecommendation(event);
}

/**
 * Submits an analyst-confirmed notification to the backend or logs in local session store.
 */
export async function postNotifyResponder(
  eventId: string,
  request: NotificationRequest,
  responderName: string,
  responderType: string
): Promise<NotificationResponse> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/events/${encodeURIComponent(eventId)}/response/notify`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(request),
      }
    );

    if (res.ok) {
      const data = (await res.json()) as NotificationResponse;
      // Also cache in local session
      localSessionActivity.unshift({
        notification_id: data.notification_id,
        event_id: data.event_id,
        responder_id: data.responder_id,
        responder_name: data.responder_name,
        responder_type: responderType as any,
        action: data.action,
        status: data.status,
        mode: data.mode,
        timestamp: data.timestamp,
        analyst_notes: request.analyst_notes,
      });
      return data;
    }
  } catch {
    // Fallback simulation
  }

  // Local deterministic simulation fallback
  const now = new Date().toISOString();
  const notifId = `NOTIF-${eventId}-${request.responder_id}-${Date.now()}`;
  const actionVerb =
    request.action === "MOBILIZE"
      ? "Mobilization request"
      : "Emergency response alert";

  const response: NotificationResponse = {
    notification_id: notifId,
    event_id: eventId,
    responder_id: request.responder_id,
    responder_name: responderName,
    action: request.action || "NOTIFY",
    status: "SIMULATED",
    mode: "SIMULATED",
    timestamp: now,
    message: `${actionVerb} simulated successfully for ${responderName}. Safe demo record logged.`,
  };

  const record: ResponseActivityRecord = {
    notification_id: notifId,
    event_id: eventId,
    responder_id: request.responder_id,
    responder_name: responderName,
    responder_type: responderType as any,
    action: request.action || "NOTIFY",
    status: "SIMULATED",
    mode: "SIMULATED",
    timestamp: now,
    analyst_notes: request.analyst_notes,
  };

  localSessionActivity.unshift(record);
  return response;
}

/**
 * Fetches historical response activity for an event.
 */
export async function fetchResponseActivity(
  eventId: string
): Promise<ResponseActivityRecord[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/events/${encodeURIComponent(eventId)}/response/activity`,
      {
        headers: { Accept: "application/json" },
      }
    );

    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.records) && data.records.length > 0) {
        return data.records as ResponseActivityRecord[];
      }
    }
  } catch {
    // Fallback
  }

  return localSessionActivity.filter((r) => r.event_id === eventId);
}
