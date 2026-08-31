/**
 * Operational Risk & Severity Intelligence Contracts
 *
 * CRITICAL SCIENTIFIC DISTINCTION:
 * - Model Confidence: "How confident is the ML model in its predicted classification?"
 * - Operational Risk: "How operationally severe / urgent is this thermal event?"
 *
 * Risk assessment is a derived frontend operational heuristic and NOT an ML confidence prediction.
 */

export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INDETERMINATE";

export interface RiskFactor {
  name: string;
  points: number;
  maxPoints: number;
  description: string;
}

export interface RiskAssessment {
  score: number; // Clamped 0-100 (or 0 when indeterminate)
  level: RiskLevel;
  factors: RiskFactor[];
  isIndeterminate: boolean;
  indeterminateReason?: string;
  summary: string;
  disclaimer: string;
}
