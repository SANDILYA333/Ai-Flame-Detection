/**
 * Canonical frontend event contracts matching packages/schemas/event.py and services/api/schemas/events.py
 */

export type PhenomenonType =
  | "fire"
  | "flare"
  | "industrial_thermal_source"
  | "agricultural_burn"
  | "vegetation_wildfire"
  | "other_thermal_anomaly"
  | "unknown"
  | "FLARE"
  | "STACK"
  | "OPEN_BURNING"
  | "HOT_SURFACE"
  | "UNKNOWN";

export type IndustrialClassification =
  | "industrial"
  | "non_industrial"
  | "unknown"
  | "INDUSTRIAL"
  | "NON_INDUSTRIAL"
  | "UNKNOWN";

export type PersistenceState =
  | "transient"
  | "recurring"
  | "persistent"
  | "insufficient_history";

export type UncertaintyState =
  | "CONFIDENT"
  | "REVIEW_REQUIRED"
  | "ABSTAINED";

/**
 * Single canonical event summary item returned by GET /events (API-006)
 */
export interface BackendEventItem {
  event_id: string;
  started_at: string; // ISO UTC
  ended_at: string; // ISO UTC
  duration_seconds: number | null;
  centroid_latitude: number;
  centroid_longitude: number;
  detection_count: number;
  mean_frp_mw: number | null;
  max_frp_mw: number | null;
  classification_state: string | null;
  persistence_state: string | null;
}

/**
 * Pagination envelope for event queries
 */
export interface EventPagination {
  total_count: number;
  limit: number;
  offset: number;
  has_next: boolean;
}

/**
 * Response structure for GET /events (API-006)
 */
export interface EventsResponse {
  service: string;
  pagination: EventPagination;
  events: BackendEventItem[];
}

/**
 * Query parameters supported by GET /events
 */
export interface EventsQueryParams {
  min_lat?: number;
  max_lat?: number;
  min_lon?: number;
  max_lon?: number;
  start_time?: string; // ISO-8601 UTC
  end_time?: string; // ISO-8601 UTC
  status?: string;
  classification_state?: string;
  limit?: number;
  offset?: number;
}

/**
 * Detailed canonical event response for GET /events/{event_id} (API-007)
 */
export interface EventDetailResponse {
  event_id: string;
  geometry: {
    type: string;
    coordinates: [number, number]; // [lon, lat]
  };
  started_at: string;
  ended_at: string;
  duration_seconds: number | null;
  detection_count: number;
  context_status: string;
  intelligence_status: string | null;
}

/**
 * Single observation in an event's chronological timeline
 */
export interface TimelineObservation {
  timestamp: string;
  detection_id: string;
  latitude: number;
  longitude: number;
  source: string;
  frp_mw: number | null;
  confidence: string | null;
}

/**
 * Timeline response for GET /events/{event_id}/timeline (API-008)
 */
export interface EventTimelineResponse {
  event_id: string;
  started_at: string;
  ended_at: string;
  timeline: TimelineObservation[];
}

/**
 * Spatial / Contextual evidence item
 */
export interface ContextEvidence {
  evidence_id?: string;
  facility_name?: string;
  distance_meters?: number;
  infrastructure_type?: string;
  confidence_score?: number;
  [key: string]: unknown;
}

/**
 * Scientific reference evidence item
 */
export interface ReferenceEvidence {
  reference_id?: string;
  source?: string;
  label?: string;
  correlation_score?: number;
  [key: string]: unknown;
}

/**
 * Evidence response for GET /events/{event_id}/evidence (API-009)
 */
export interface EventEvidenceResponse {
  event_id: string;
  context_evidence: ContextEvidence[];
  reference_evidence: ReferenceEvidence[];
}

/**
 * High-level UI ViewModel for map and dashboard consumption
 */
export interface ThermalEvent {
  event_id: string;
  latitude: number;
  longitude: number;
  phenomenon: PhenomenonType;
  classification: IndustrialClassification;
  confidence: number;
  uncertainty_state: UncertaintyState;
  frp_mw: number;
  detection_count: number;
  start_time: string;
  end_time: string;
  source_id?: string;
  is_persistent?: boolean;
  location_name?: string;
  context_summary?: string;
  satellite_instrument?: string;
}

/**
 * Converts a backend canonical event item into the UI ThermalEvent rendering model
 */
export function backendEventToThermalEvent(item: BackendEventItem): ThermalEvent {
  const rawClass = item.classification_state?.toLowerCase();
  let classification: IndustrialClassification = "UNKNOWN";
  if (rawClass === "industrial") {
    classification = "INDUSTRIAL";
  } else if (rawClass === "non_industrial") {
    classification = "NON_INDUSTRIAL";
  }

  const isUnknown = classification === "UNKNOWN";
  const isReviewRequired =
    item.persistence_state === "insufficient_history" || isUnknown;

  const frp = item.max_frp_mw ?? item.mean_frp_mw ?? 25.0;
  const confidence = rawClass === "industrial" ? 0.94 : isUnknown ? 0.45 : 0.82;

  const latStr = `${Math.abs(item.centroid_latitude).toFixed(2)}°${item.centroid_latitude >= 0 ? "N" : "S"}`;
  const lonStr = `${Math.abs(item.centroid_longitude).toFixed(2)}°${item.centroid_longitude >= 0 ? "E" : "W"}`;

  return {
    event_id: item.event_id,
    latitude: item.centroid_latitude,
    longitude: item.centroid_longitude,
    phenomenon: "FLARE",
    classification,
    confidence,
    uncertainty_state: isReviewRequired ? "REVIEW_REQUIRED" : "CONFIDENT",
    frp_mw: frp,
    detection_count: item.detection_count,
    start_time: item.started_at,
    end_time: item.ended_at,
    is_persistent:
      item.persistence_state === "persistent" || item.persistence_state === "recurring",
    location_name: `Thermal Anomaly Cluster (${latStr}, ${lonStr})`,
    context_summary: `State: ${item.classification_state ?? "unclassified"} · Persistence: ${
      item.persistence_state ?? "transient"
    } · ${item.detection_count} detections`,
  };
}
