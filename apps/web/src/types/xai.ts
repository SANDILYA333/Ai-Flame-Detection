import { IndustrialClassification, UncertaintyState } from "./event";

export type SignalImpact = "supports_industrial" | "supports_non_industrial" | "indeterminate";
export type SignalStatus = "positive" | "negative" | "neutral" | "missing";

export interface EvidenceSignal {
  id: string;
  name: string;
  value: string;
  status: SignalStatus;
  impact: SignalImpact;
  description: string;
}

export interface ModelProvenance {
  modelName: string;
  modelVersion: string;
  featureSchema: string;
  operatingMode: string;
  decisionThreshold: number;
  calibrationStatus: string;
}

export interface ClassProbability {
  className: IndustrialClassification;
  label: string;
  percentage: number;
  color: string;
}

export interface XaiExplanation {
  eventId: string;
  assignedClass: IndustrialClassification;
  confidence: number;
  uncertaintyState: UncertaintyState;
  isAbstained: boolean;
  abstentionReason: string | null;
  probabilities: ClassProbability[];
  signals: EvidenceSignal[];
  decisionSummary: string;
  provenance: ModelProvenance;
  disclaimer: string;
  attributionMethod?: string;
  shapAttributions?: Array<{
    feature: string;
    raw_feature_name: string;
    value?: string | number | boolean | null;
    shap_value: number;
    impact: string;
    description: string;
  }>;
}
