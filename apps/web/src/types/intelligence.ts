/**
 * Intelligence & evidence contracts matching packages/schemas/intelligence.py
 */

export interface UncertaintyMetric {
  model_probability: number | null;
  calibrated_confidence: number | null;
  data_quality_score: number | null;
  abstention_recommended: boolean;
  abstention_reason: string | null;
}

export interface EvidenceCategoryState {
  category: string;
  status: "available" | "missing" | "unavailable" | "not_found_in_source" | "unknown";
  details: string | null;
}

export interface EvidenceCompleteness {
  categories: EvidenceCategoryState[];
  available_count: number;
  total_expected_count: number;
  completeness_ratio: number | null;
}

export interface TemporalBaselineTelemetry {
  recurrence_90d: number;
  historical_mean_frp: number;
  historical_std_frp: number;
  sample_count: number;
  active_calendar_days: number;
  frp_z_score: number;
  frp_surge_ratio: number;
  operational_status: string;
  is_critical_anomaly: boolean;
  window_days: number;
  radius_km: number;
  is_cold_start: boolean;
}

export interface PyrometryTelemetry {
  available: boolean;
  emitter_temp_k: number;
  emitter_area_m2: number;
  fractional_area_p?: number | null;
  background_temp_k: number;
  mwir_radiance_observed?: number | null;
  lwir_radiance_observed?: number | null;
  radiance_residual?: number | null;
  is_valid: boolean;
  convergence_status: string;
  phenomenon_tag: string;
  pixel_area_m2?: number;
}

export interface FeatureAttributionTelemetry {
  feature: string;
  raw_feature_name: string;
  value?: string | number | boolean | null;
  shap_value: number;
  impact: "supports_predicted" | "opposes_predicted" | "neutral" | string;
  description: string;
}

export interface ShapExplanationTelemetry {
  target_class: string;
  base_value: number;
  predicted_probability: number;
  attribution_method: string;
  attributions: FeatureAttributionTelemetry[];
}

export interface IntelligenceResult {
  intelligence_id: string;
  event_id: string;
  phenomenon: string;
  context: string;
  persistence: string;
  attribution: string;
  uncertainty: UncertaintyMetric;
  evidence_completeness: EvidenceCompleteness;
  created_at: string;
  temporal_baseline?: TemporalBaselineTelemetry | null;
  pyrometry?: PyrometryTelemetry | null;
  xai?: ShapExplanationTelemetry | null;
  source_id?: string | null;
  pipeline_run_id?: string | null;
  model_version?: string | null;
  configuration_version?: string | null;
  notes?: string | null;
}

export interface IntelligenceSummary {
  total_events: number;
  industrial_count: number;
  non_industrial_count: number;
  unknown_count: number;
  review_required_count: number;
  model_name: string;
  model_version: string;
  feature_schema_version: string;
  data_freshness_utc: string;
}
