export type ResponderType =
  | "FIRE_STATION"
  | "CHEMICAL_FIRE_STATION"
  | "INDUSTRIAL_FIRE_SAFETY"
  | "MUNICIPAL_FIRE_STATION"
  | "HOSPITAL"
  | "BURN_ICU"
  | "BURN_INTENSIVE_CARE_HOSPITAL"
  | "SPECIALIZED_HAZMAT_UNIT"
  | "PORT_EMERGENCY_SERVICES"
  | "NDRF"
  | "NDRF_DISASTER_BATTALION"
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
  | "PROVIDER_ACCEPTED"
  | "DELIVERED"
  | "PARTIAL"
  | "DUPLICATE_SUPPRESSED"
  | "FAILED"
  | "UNKNOWN"
  | "CANCELLED";

export type NotificationMode = "SIMULATED" | "LIVE";

export type EscalationState =
  | "NO_ESCALATION"
  | "ADMIN_REVIEW_REQUIRED"
  | "AUTOMATIC_ESCALATION";

export type EscalationType =
  | "NO_ESCALATION"
  | "ADMIN_REVIEW"
  | "ADMIN_CONFIRMED"
  | "HIGH_CONFIDENCE_AUTO"
  | "CRITICAL_MEDICAL";

export type NotificationChannel = "SMS" | "WHATSAPP";

export type ChannelDeliveryStatus =
  | "SENT"
  | "PROVIDER_ACCEPTED"
  | "DELIVERED"
  | "SIMULATED"
  | "DUPLICATE_SUPPRESSED"
  | "FAILED"
  | "TIMEOUT"
  | "PROVIDER_REJECTED"
  | "UNKNOWN";

export interface EscalationDecision {
  event_id: string;
  confidence: number | null;
  operational_priority: ResponsePriority;
  escalation_state: EscalationState;
  automatic: boolean;
  medical_escalation: boolean;
  policy_drivers: string[];
  evaluated_at: string;
  policy_version: string;
}

export interface ChannelResult {
  channel: NotificationChannel;
  status: ChannelDeliveryStatus;
  recipient: string;
  destination_masked?: string | null;
  message: string;
  provider?: string | null;
  provider_message_id?: string | null;
  correlation_id?: string | null;
  submitted_at?: string | null;
  delivered_at?: string | null;
  retry_count?: number;
  error_details?: string | null;
}

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
  estimated_eta_minutes?: number | null;
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
  confidence?: number;
  auto_escalation_eligible?: boolean;
  auto_escalation_triggered?: boolean;
  escalation_type?: EscalationType | null;
  medical_escalation?: boolean;
  policy_drivers?: string[];
  escalation_decision?: EscalationDecision | null;
  is_routine_flare: boolean;
  is_abstained_or_unknown: boolean;
  responders: EmergencyResponder[];
  nearest_hospitals?: EmergencyResponder[];
  nearest_fire_stations?: EmergencyResponder[];
  specialized_responders?: EmergencyResponder[];
  ndrf_responders?: EmergencyResponder[];
  recommendation_basis: string[];
  evaluated_at: string;
}

export interface NotificationRequest {
  responder_id: string;
  action?: NotificationAction;
  mode?: NotificationMode;
  recipient_phone?: string;
  channels?: NotificationChannel[];
  escalation_type?: EscalationType;
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
  escalation_type?: EscalationType;
  trigger_source?: EscalationType;
  recipient_phone?: string | null;
  destination_masked?: string | null;
  correlation_id?: string | null;
  channels?: ChannelResult[];
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
  escalation_type?: EscalationType;
  trigger_source?: EscalationType;
  recipient_phone?: string | null;
  destination_masked?: string | null;
  correlation_id?: string | null;
  channels?: ChannelResult[];
  timestamp: string;
  analyst_notes?: string;
}
