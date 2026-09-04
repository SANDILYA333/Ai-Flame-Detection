import { apiFetch } from "./client";

export interface ForestFeatureProperties {
  forest_id: string;
  osm_id: number;
  osm_type: string;
  osm_identity: string;
  name: string;
  name_en?: string;
  country_code: string;
  region?: string;
  forest_type: string;
  osm_tag: string;
  area_km2: number;
  centroid: {
    latitude: number;
    longitude: number;
  };
  metadata?: Record<string, string>;
  source: string;
  is_repaired: boolean;
}

export interface ForestGeoJsonFeature {
  type: "Feature";
  id?: string;
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: any;
  };
  properties: ForestFeatureProperties;
}

export interface ForestGeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: ForestGeoJsonFeature[];
  bbox?: number[];
}

export interface NearbyForestItem {
  id: string;
  osm_identity: string;
  name: string | null;
  country_code: string;
  forest_type: string;
  osm_tag: string;
  distance_km: number;
  area_km2: number;
  centroid: {
    latitude: number;
    longitude: number;
  };
}

export interface NearbyForestsResponse {
  latitude: number;
  longitude: number;
  radius_km: number;
  total_found: number;
  forests: NearbyForestItem[];
}

export interface NearbyForestThreatItemResponse {
  forest_id: string;
  osm_identity: string;
  name: string | null;
  country_code: string;
  forest_type: string;
  osm_tag: string;
  distance_km: number;
  inside_forest: boolean;
  is_within_threat_radius: boolean;
  threat_level: "INSIDE_FOREST" | "CRITICAL" | "WARNING" | "AWARENESS" | "HIGH" | "MODERATE" | "NONE";
  nearest_point?: {
    latitude: number;
    longitude: number;
  } | null;
  centroid: {
    latitude: number;
    longitude: number;
  };
  area_km2: number;
}

export interface ThreatConfigurationModel {
  search_radius_km: number;
  threat_radius_km: number;
  awareness_radius_km?: number;
  warning_radius_km?: number;
  critical_radius_km?: number;
  high_radius_km?: number;
  moderate_radius_km?: number;
}

export interface ForestThreatAssessmentResponse {
  success: boolean;
  fire_event_id?: string | null;
  fire_coordinate: {
    latitude: number;
    longitude: number;
  };
  configuration: ThreatConfigurationModel;
  is_threatened: boolean;
  threat_level: "INSIDE_FOREST" | "CRITICAL" | "WARNING" | "AWARENESS" | "HIGH" | "MODERATE" | "NONE";
  nearest_forest?: NearbyForestThreatItemResponse | null;
  nearby_forests: NearbyForestThreatItemResponse[];
  total_threatened_forests: number;
  evaluated_at: string;
}

export interface ForestProximityAlertRequest {
  event_id: string;
  forest_id: string;
  fire_confidence?: number;
  recipient_phone?: string | null;
  channels?: string[];
  force_dispatch?: boolean;
}

export interface ForestProximityAlertResponse {
  success: boolean;
  alert_id: string;
  event_id: string;
  forest_id: string;
  forest_name: string | null;
  distance_km: number;
  inside_forest: boolean;
  threat_level: string;
  is_escalation: boolean;
  notification_dispatched: boolean;
  notification_id?: string | null;
  created_at: string;
}

/**
 * Fetch OpenStreetMap forest polygons as GeoJSON FeatureCollection.
 */
export async function fetchForestsGeoJson(params: {
  country?: string;
  bbox?: string;
  forest_type?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ForestGeoJsonFeatureCollection> {
  return apiFetch<ForestGeoJsonFeatureCollection>("/forests", {
    params: {
      country: params.country,
      bbox: params.bbox,
      forest_type: params.forest_type,
      search: params.search,
      limit: params.limit ?? 100,
      offset: params.offset ?? 0,
    },
    timeoutMs: 8000,
  });
}

/**
 * Fetch nearby forests relative to a coordinate.
 */
export async function fetchNearbyForests(
  latitude: number,
  longitude: number,
  radiusKm = 25.0,
  limit = 50
): Promise<NearbyForestsResponse> {
  return apiFetch<NearbyForestsResponse>("/forests/nearby", {
    params: {
      latitude,
      longitude,
      radius_km: radiusKm,
      limit,
    },
    timeoutMs: 8000,
  });
}

/**
 * Fetch forest threat assessment for a specific thermal event.
 */
export async function fetchForestThreatForEvent(
  eventId: string,
  searchRadiusKm?: number,
  threatRadiusKm?: number
): Promise<ForestThreatAssessmentResponse> {
  return apiFetch<ForestThreatAssessmentResponse>(`/forests/threat/${encodeURIComponent(eventId)}`, {
    params: {
      search_radius_km: searchRadiusKm,
      threat_radius_km: threatRadiusKm,
    },
    timeoutMs: 8000,
  });
}

/**
 * Evaluate forest proximity threat for arbitrary coordinates.
 */
export async function evaluateForestThreatForPoint(
  latitude: number,
  longitude: number,
  fireEventId?: string,
  searchRadiusKm?: number,
  threatRadiusKm?: number
): Promise<ForestThreatAssessmentResponse> {
  return apiFetch<ForestThreatAssessmentResponse>("/forests/threat/evaluate", {
    params: {
      latitude,
      longitude,
      fire_event_id: fireEventId,
      search_radius_km: searchRadiusKm,
      threat_radius_km: threatRadiusKm,
    },
    timeoutMs: 8000,
  });
}

export interface ForestThreatCandidateEvent {
  event_id: string;
  coordinate: {
    latitude: number;
    longitude: number;
  };
  distance_km: number;
  inside_forest: boolean;
  threat_level: string;
  confidence: number;
  frp_mw: number;
  classification: string;
  detected_at?: string | null;
}

export interface ForestThreatSummaryItem {
  forest_id: string;
  osm_identity: string;
  name: string | null;
  country_code: string;
  forest_type: string;
  osm_tag: string;
  area_km2: number;
  centroid: {
    latitude: number;
    longitude: number;
  };
  threat_level: "ACTIVE_FIRE" | "CRITICAL" | "WARNING" | "AWARENESS" | "SAFE" | string;
  inside_forest: boolean;
  primary_event_id?: string | null;
  primary_distance_km?: number | null;
  primary_confidence?: number | null;
  primary_frp_mw?: number | null;
  active_threat_count: number;
  why_at_risk: string[];
  progression_trend: string;
  evaluated_at: string;
}

export interface GlobalForestMonitoringSummary {
  total_monitored_forests: number;
  safe_forests: number;
  awareness_forests: number;
  warning_forests: number;
  critical_forests: number;
  active_fire_forests: number;
  total_threatened_forests: number;
  active_thermal_events_evaluated: number;
  evaluated_at: string;
}

export interface ForestMonitoringDashboardResponse {
  success: boolean;
  summary: GlobalForestMonitoringSummary;
  total_filtered: number;
  limit: number;
  offset: number;
  forests: ForestThreatSummaryItem[];
}

export interface ForestDetailRecord {
  id: string;
  osm_id: number;
  osm_type: string;
  osm_identity: string;
  name: string | null;
  name_en?: string | null;
  country_code: string;
  region?: string | null;
  forest_type: string;
  osm_tag: string;
  area_km2: number;
  centroid: {
    latitude: number;
    longitude: number;
  };
  geometry: {
    type: string;
    coordinates: any;
  };
  metadata: Record<string, string>;
  source: string;
  is_repaired: boolean;
}

export interface ForestThreatDetailResponse {
  success: boolean;
  forest: ForestDetailRecord;
  threat_level: string;
  is_threatened: boolean;
  inside_forest: boolean;
  nearest_event_id?: string | null;
  nearest_distance_km?: number | null;
  nearest_point?: {
    latitude: number;
    longitude: number;
  } | null;
  primary_confidence?: number | null;
  primary_frp_mw?: number | null;
  threatening_events: ForestThreatCandidateEvent[];
  why_at_risk: string[];
  progression_trend: string;
  evaluated_at: string;
}

/**
 * Fetch global forest monitoring dashboard and prioritized threatened list.
 */
export async function fetchForestMonitoringDashboard(params: {
  status?: string;
  country?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ForestMonitoringDashboardResponse> {
  return apiFetch<ForestMonitoringDashboardResponse>("/forests/threats/monitoring", {
    params: {
      status: params.status,
      country: params.country,
      search: params.search,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    },
    timeoutMs: 10000,
  });
}

/**
 * Fetch detailed threat intelligence report for a single forest.
 */
export async function fetchForestThreatDetail(
  forestId: string
): Promise<ForestThreatDetailResponse> {
  return apiFetch<ForestThreatDetailResponse>(
    `/forests/threats/forest/${encodeURIComponent(forestId)}`,
    {
      timeoutMs: 8000,
    }
  );
}

/**
 * Fetch single forest detail by ID.
 */
export async function fetchForestDetailById(
  forestId: string
): Promise<ForestDetailRecord> {
  return apiFetch<ForestDetailRecord>(`/forests/${encodeURIComponent(forestId)}`, {
    timeoutMs: 8000,
  });
}

/**
 * Dispatch proximity alert and trigger emergency notifications.
 */
export async function dispatchForestProximityAlert(
  payload: ForestProximityAlertRequest
): Promise<ForestProximityAlertResponse> {
  return apiFetch<ForestProximityAlertResponse>("/forests/threat/alert", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    timeoutMs: 10000,
  });
}



