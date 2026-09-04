"use client";

import React, { useMemo } from "react";
import { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import { IntelligenceResult } from "@/types/intelligence";
import { generateXaiExplanation } from "@/lib/xai/explainer";
import {
  Brain,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Cpu,
  Layers,
  ShieldCheck,
  Zap,
  Clock,
  Building2,
  Radio,
  FileCode2,
  Info,
  Sliders,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

export interface ExplainableAiSectionProps {
  event: ThermalEvent;
  evidence?: EventEvidenceResponse | null;
  intelligence?: IntelligenceResult | null;
  className?: string;
}

export function ExplainableAiSection({
  event,
  evidence,
  intelligence,
  className,
}: ExplainableAiSectionProps) {
  const xai = useMemo(
    () => generateXaiExplanation(event, evidence, intelligence),
    [event, evidence, intelligence]
  );

  return (
    <div
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-2.5",
        className
      )}
    >
      {/* 1. Header: XAI Title & Model Lineage */}
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div className="flex items-center gap-1.5 text-foreground">
          <Brain className="w-3.5 h-3.5 text-accent" />
          <span className="text-[11px] font-bold tracking-wider uppercase">
            Why This Classification? (XAI)
          </span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface border border-border text-foreground-muted font-mono">
            {xai.provenance.operatingMode}
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/10 border border-accent/30 text-accent font-semibold">
            {(xai.confidence * 100).toFixed(1)}% CONF
          </span>
        </div>
      </div>

      {/* 2. Decision Summary Banner */}
      <div
        className={cn(
          "p-2 rounded-control border text-[10px] leading-relaxed",
          xai.isAbstained
            ? "bg-accent-cyan/10 border-accent-cyan/30 text-accent-cyan"
            : xai.assignedClass === "INDUSTRIAL"
            ? "bg-accent/10 border-accent/30 text-foreground-secondary"
            : "bg-state-success/10 border-state-success/30 text-foreground-secondary"
        )}
      >
        <div className="font-bold mb-0.5 flex items-center gap-1">
          {xai.isAbstained ? (
            <>
              <AlertTriangle className="w-3 h-3 text-state-warning" />
              <span>CLASSIFICATION DECISION: ABSTAINED / REVIEW</span>
            </>
          ) : (
            <>
              <ShieldCheck className="w-3 h-3 text-accent" />
              <span>CLASSIFICATION DECISION: {xai.assignedClass}</span>
            </>
          )}
        </div>
        <div className="text-[9.5px] text-foreground-muted">{xai.decisionSummary}</div>
      </div>

      {/* 3. SHAP Feature Attribution / Sharp Weights */}
      {xai.shapAttributions && xai.shapAttributions.length > 0 && (
        <div className="space-y-1.5 pt-1 border-t border-border/60">
          <div className="flex items-center justify-between text-[9px] uppercase tracking-wider text-foreground-muted font-semibold">
            <div className="flex items-center gap-1">
              <Sliders className="w-3 h-3 text-accent" />
              <span>SHAP Feature Attribution (Sharp Weights)</span>
            </div>
            <span className="text-[8px] px-1.5 py-0.2 rounded bg-surface border border-border text-accent font-bold">
              {xai.attributionMethod || "TREE_SHAP"}
            </span>
          </div>

          <div className="space-y-1.5">
            {xai.shapAttributions.slice(0, 5).map((attr) => {
              const isPositive = attr.shap_value >= 0;
              const absVal = Math.min(1.0, Math.abs(attr.shap_value));
              const pctWidth = Math.max(10, Math.round(absVal * 100));

              return (
                <div
                  key={attr.raw_feature_name}
                  className="p-1.5 rounded bg-background/60 border border-border/40 text-[9.5px] space-y-1"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-foreground truncate">
                      {attr.feature}
                    </span>
                    <div className="flex items-center gap-1 shrink-0 font-mono">
                      {attr.value !== undefined && attr.value !== null && (
                        <span className="text-[9px] text-foreground-muted">
                          [{String(attr.value)}]
                        </span>
                      )}
                      <span
                        className={cn(
                          "text-[9px] font-bold px-1 rounded",
                          isPositive
                            ? "bg-accent/15 text-accent"
                            : "bg-state-warning/15 text-state-warning"
                        )}
                      >
                        {isPositive ? `+${attr.shap_value.toFixed(3)}` : attr.shap_value.toFixed(3)}
                      </span>
                    </div>
                  </div>

                  {/* Impact weight visual bar */}
                  <div className="w-full h-1 bg-surface-hover rounded-full overflow-hidden flex items-center">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        isPositive ? "bg-accent" : "bg-state-warning"
                      )}
                      style={{ width: `${pctWidth}%` }}
                    />
                  </div>

                  <p className="text-[8.5px] text-foreground-secondary leading-snug">
                    {attr.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Evidence Checklist / Signal Matrix */}
      <div className="space-y-1.5 pt-1 border-t border-border/60">
        <div className="text-[9px] uppercase tracking-wider text-foreground-muted font-semibold flex items-center justify-between">
          <span>Grounded Evidence Signals</span>
          <span className="text-[8.5px] text-foreground-muted/70">Threshold: 0.70</span>
        </div>

        <div className="space-y-1 text-[10px]">
          {xai.signals.map((signal) => (
            <div
              key={signal.id}
              className="p-1.5 rounded bg-background/50 border border-border/40 flex items-start gap-2"
            >
              <div className="shrink-0 mt-0.5">
                {signal.status === "positive" && (
                  <CheckCircle2 className="w-3 h-3 text-state-success" />
                )}
                {signal.status === "negative" && (
                  <AlertTriangle className="w-3 h-3 text-state-warning" />
                )}
                {signal.status === "neutral" && (
                  <HelpCircle className="w-3 h-3 text-foreground-muted" />
                )}
                {signal.status === "missing" && (
                  <HelpCircle className="w-3 h-3 text-accent-cyan" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span className="font-semibold text-foreground truncate">{signal.name}</span>
                  <span
                    className={cn(
                      "text-[9px] font-bold shrink-0",
                      signal.impact === "supports_industrial"
                        ? "text-accent"
                        : signal.impact === "supports_non_industrial"
                        ? "text-state-warning"
                        : "text-accent-cyan"
                    )}
                  >
                    {signal.impact === "supports_industrial"
                      ? "Supports Industrial"
                      : signal.impact === "supports_non_industrial"
                      ? "Supports Non-Ind"
                      : "Indeterminate"}
                  </span>
                </div>
                <div className="text-[9.5px] text-foreground-secondary mt-0.5">
                  {signal.value}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Calibrated Class Probabilities Breakdown */}
      <div className="space-y-1 pt-1.5 border-t border-border/60 text-[10px]">
        <div className="text-[9px] uppercase tracking-wider text-foreground-muted font-semibold">
          Calibrated Class Probabilities
        </div>

        <div className="space-y-1 pt-0.5">
          {xai.probabilities.map((prob) => (
            <div key={prob.className} className="space-y-0.5">
              <div className="flex items-center justify-between text-[9px] text-foreground-secondary">
                <span>{prob.label}</span>
                <span className="font-semibold text-foreground">{prob.percentage}%</span>
              </div>
              <div className="w-full h-1.5 bg-background rounded-full overflow-hidden border border-border/40">
                <div
                  className="h-full transition-all duration-300"
                  style={{
                    width: `${prob.percentage}%`,
                    backgroundColor: prob.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 6. Provenance & Scientific Lineage Footer */}
      <div className="pt-2 border-t border-border/50 text-[8.5px] text-foreground-muted flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Cpu className="w-2.5 h-2.5 text-accent" />
          <span>{xai.provenance.modelName}</span>
        </div>
        <div className="flex items-center gap-1 text-accent-cyan">
          <FileCode2 className="w-2.5 h-2.5" />
          <span>{xai.provenance.featureSchema}</span>
        </div>
      </div>
    </div>
  );
}
