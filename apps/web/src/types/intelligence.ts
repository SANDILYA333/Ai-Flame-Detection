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
