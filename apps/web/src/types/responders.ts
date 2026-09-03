export type ResponderType =
  | "FIRE_STATION"
  | "CHEMICAL_FIRE_STATION"
  | "HOSPITAL"
  | "BURN_ICU"
  | "NDRF"
  | "OTHER";

export type ResponsePriority =
  | "CRITICAL"
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "MONITOR_ONLY"
  | "REVIEW_REQUIRED";

export type NotificationAction = "NOTIFY" | "MOBILIZE";

export type NotificationStatus =
  | "READY"
  | "CONFIRMING"
  | "PROCESSING"
  | "SIMULATED"
  | "SENT"
  | "FAILED"
  | "CANCELLED";

export type NotificationMode = "SIMULATED" | "LIVE";

export interface EmergencyResponder {
  id: string;
  name: string;
  type: ResponderType;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  distance_meters: number;
  formatted_distance: string;
  estimated_eta_minutes: number;
  formatted_eta: string;
  capabilities: string[];
  phone: string;
  jurisdiction: string;
  source: string;
  recommendation_reason: string;
  plume_impact_status?: string;
}

export interface EventResponseRecommendation {
  event_id: string;
  response_priority: ResponsePriority;
  priority_reason: string;
  is_routine_flare: boolean;
  is_abstained_or_unknown: boolean;
  responders: EmergencyResponder[];
  recommendation_basis: string[];
  evaluated_at: string;
}

export interface NotificationRequest {
  responder_id: string;
  action?: NotificationAction;
  mode?: NotificationMode;
  analyst_notes?: string;
}

export interface NotificationResponse {
  notification_id: string;
  event_id: string;
  responder_id: string;
  responder_name: string;
  action: NotificationAction;
  status: NotificationStatus;
  mode: NotificationMode;
  timestamp: string;
  message: string;
}

export interface ResponseActivityRecord {
  notification_id: string;
  event_id: string;
  responder_id: string;
  responder_name: string;
  responder_type: ResponderType;
  action: NotificationAction;
  status: NotificationStatus;
  mode: NotificationMode;
  timestamp: string;
  analyst_notes?: string;
}
