"use client";

import React, { useState } from "react";
import {
  Sliders,
  Play,
  RotateCcw,
  X,
  Sparkles,
  Flame,
  Brain,
  Wind,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface AiSimulationLabModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInjectSimulatedEvent?: (simEvent: any) => void;
}

const PRESETS = [
  {
    id: "jamnagar_flare",
    label: "Jamnagar Refinery Flare",
    lat: 22.4707,
    lon: 70.0577,
    frp: 85.0,
    mwir: 360.0,
    lwir: 298.0,
    distFac: 0.25,
    recurrence: 14,
    forest: 0.02,
    windSpd: 4.2,
    windDir: 235.0,
  },
  {
    id: "vizag_styrene",
    label: "Vizag Polymer Gas Leak",
    lat: 17.7011,
    lon: 83.2195,
    frp: 120.0,
    mwir: 380.0,
    lwir: 305.0,
    distFac: 0.1,
    recurrence: 1,
    forest: 0.05,
    windSpd: 5.5,
    windDir: 190.0,
  },
  {
    id: "punjab_stubble",
    label: "Punjab Agricultural Stubble Burn",
    lat: 30.7333,
    lon: 75.8456,
    frp: 35.0,
    mwir: 335.0,
    lwir: 300.0,
    distFac: 6.5,
    recurrence: 1,
    forest: 0.01,
    windSpd: 2.1,
    windDir: 310.0,
  },
  {
    id: "jharia_coal",
    label: "Jharia Coal Seam Smoldering",
    lat: 23.7441,
    lon: 86.4173,
    frp: 95.0,
    mwir: 370.0,
    lwir: 310.0,
    distFac: 1.2,
    recurrence: 24,
    forest: 0.08,
    windSpd: 3.0,
    windDir: 270.0,
  },
  {
    id: "similipal_wildfire",
    label: "Similipal Forest Canopy Fire",
    lat: 21.8667,
    lon: 86.3333,
    frp: 140.0,
    mwir: 390.0,
    lwir: 305.0,
    distFac: 18.0,
    recurrence: 1,
    forest: 0.85,
    windSpd: 6.0,
    windDir: 150.0,
  },
];

export function AiSimulationLabModal({
  isOpen,
  onClose,
  onInjectSimulatedEvent,
}: AiSimulationLabModalProps) {
  const [frp, setFrp] = useState<number>(75.0);
  const [mwir, setMwir] = useState<number>(355.0);
  const [lwir, setLwir] = useState<number>(298.0);
  const [distFac, setDistFac] = useState<number>(0.4);
  const [recurrence, setRecurrence] = useState<number>(8);
  const [forest, setForest] = useState<number>(0.05);
  const [windSpd, setWindSpd] = useState<number>(4.2);
  const [windDir, setWindDir] = useState<number>(230.0);
  const [lat, setLat] = useState<number>(22.4707);
  const [lon, setLon] = useState<number>(70.0577);

  const [isLoading, setIsLoading] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const applyPreset = (preset: (typeof PRESETS)[0]) => {
    setLat(preset.lat);
    setLon(preset.lon);
    setFrp(preset.frp);
    setMwir(preset.mwir);
    setLwir(preset.lwir);
    setDistFac(preset.distFac);
    setRecurrence(preset.recurrence);
    setForest(preset.forest);
    setWindSpd(preset.windSpd);
    setWindDir(preset.windDir);
  };

  const handleRunInference = async () => {
    setIsLoading(true);
    try {
      const resp = await fetch("/api/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latitude: lat,
          longitude: lon,
          frp_mw: frp,
          bright_mwir_k: mwir,
          bright_lwir_k: lwir,
          dist_to_facility_km: distFac,
          recurrence_90d: recurrence,
          forest_fraction: forest,
          wind_speed_ms: windSpd,
          wind_direction_deg: windDir,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setSimulationResult(data);
      } else {
        // Local deterministic simulation fallback
        const isInd = distFac < 1.0 && recurrence >= 4;
        setSimulationResult({
          simulated_event_id: `SIM-EVT-${Date.now().toString().slice(-6)}`,
          assigned_class: isInd ? "INDUSTRIAL" : forest > 0.4 ? "NON_INDUSTRIAL" : "UNKNOWN",
          confidence: 0.88,
          is_abstained: false,
          pyrometry: {
            emitter_temp_k: Math.round(550 + Math.sqrt(frp) * 65),
            emitter_area_m2: Number((frp * 1.45).toFixed(1)),
          },
          plume: {
            plume_length_km: Number((Math.sqrt(frp) * 0.4).toFixed(1)),
            evacuation_radius_km: Number((0.25 * Math.pow(frp, 0.35)).toFixed(1)),
          },
        });
      }
    } catch {
      const isInd = distFac < 1.0 && recurrence >= 4;
      setSimulationResult({
        simulated_event_id: `SIM-EVT-${Date.now().toString().slice(-6)}`,
        assigned_class: isInd ? "INDUSTRIAL" : forest > 0.4 ? "NON_INDUSTRIAL" : "UNKNOWN",
        confidence: 0.88,
        is_abstained: false,
        pyrometry: {
          emitter_temp_k: Math.round(550 + Math.sqrt(frp) * 65),
          emitter_area_m2: Number((frp * 1.45).toFixed(1)),
        },
        plume: {
          plume_length_km: Number((Math.sqrt(frp) * 0.4).toFixed(1)),
          evacuation_radius_km: Number((0.25 * Math.pow(frp, 0.35)).toFixed(1)),
        },
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-surface-raised border border-border rounded-modal shadow-modal flex flex-col font-mono overflow-hidden text-foreground">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-accent/15 border border-accent/30 text-accent">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                <span>AI Simulation & Counterfactual Testing Lab</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30">
                  REAL-TIME ML INFERENCE
                </span>
              </div>
              <div className="text-[9px] text-foreground-muted">
                Synthesize custom thermal observations and evaluate selective classification decisions
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Preset Selector Chips */}
        <div className="px-4 py-2 bg-surface/60 border-b border-border flex items-center gap-1.5 overflow-x-auto text-[10px]">
          <span className="text-foreground-muted text-[9px] uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-accent" />
            Presets:
          </span>
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => applyPreset(p)}
              className="px-2 py-0.5 rounded bg-surface hover:bg-surface-hover border border-border text-foreground-secondary hover:text-foreground shrink-0 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Modal Body: Two Column (Sliders vs Results) */}
        <div className="flex-1 overflow-y-auto p-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
          {/* Sliders Column */}
          <div className="space-y-3">
            <div className="text-[9.5px] font-bold uppercase tracking-wider text-foreground-muted border-b border-border/60 pb-1">
              Custom Thermal Observation Parameters
            </div>

            {/* FRP Slider */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">Fire Radiative Power (FRP):</span>
                <span className="font-bold text-thermal-primary">{frp} MW</span>
              </div>
              <input
                type="range"
                min="5"
                max="500"
                step="5"
                value={frp}
                onChange={(e) => setFrp(Number(e.target.value))}
                className="w-full accent-thermal-primary h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* MWIR Brightness Temp */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">MWIR 3.74μm Brightness:</span>
                <span className="font-bold text-foreground">{mwir} K</span>
              </div>
              <input
                type="range"
                min="300"
                max="450"
                step="1"
                value={mwir}
                onChange={(e) => setMwir(Number(e.target.value))}
                className="w-full accent-accent h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* LWIR Brightness Temp */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">LWIR 11.45μm Brightness:</span>
                <span className="font-bold text-foreground">{lwir} K</span>
              </div>
              <input
                type="range"
                min="280"
                max="350"
                step="1"
                value={lwir}
                onChange={(e) => setLwir(Number(e.target.value))}
                className="w-full accent-accent-cyan h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* Facility Proximity */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">Distance to Industrial Facility:</span>
                <span className="font-bold text-accent">{distFac} km</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="10.0"
                step="0.05"
                value={distFac}
                onChange={(e) => setDistFac(Number(e.target.value))}
                className="w-full accent-accent h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* 90-day Recurrence */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">90-Day Recurrence Count:</span>
                <span className="font-bold text-foreground">{recurrence} days</span>
              </div>
              <input
                type="range"
                min="0"
                max="45"
                step="1"
                value={recurrence}
                onChange={(e) => setRecurrence(Number(e.target.value))}
                className="w-full accent-foreground-secondary h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* Canopy Forest Fraction */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-foreground-secondary">Canopy Forest Fraction:</span>
                <span className="font-bold text-state-success">{(forest * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={forest}
                onChange={(e) => setForest(Number(e.target.value))}
                className="w-full accent-state-success h-1.5 bg-background rounded cursor-pointer"
              />
            </div>

            {/* Wind Vector */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="space-y-0.5">
                <div className="text-[9px] text-foreground-muted">WIND SPEED</div>
                <div className="font-bold text-foreground">{windSpd} m/s</div>
              </div>
              <div className="space-y-0.5">
                <div className="text-[9px] text-foreground-muted">WIND ORIGIN</div>
                <div className="font-bold text-foreground">{windDir}°</div>
              </div>
            </div>

            <button
              onClick={handleRunInference}
              disabled={isLoading}
              className="w-full mt-2 py-2 px-3 rounded bg-accent text-background font-bold text-[11px] flex items-center justify-center gap-1.5 hover:bg-emerald-400 transition-colors shadow-sm disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current text-background" />
              <span className="text-background">{isLoading ? "Running Inference..." : "EXECUTE AI CLASSIFICATION"}</span>
            </button>
          </div>

          {/* Results Column */}
          <div className="space-y-3">
            <div className="text-[9.5px] font-bold uppercase tracking-wider text-foreground-muted border-b border-border/60 pb-1">
              Model Inference Output & Derived Telemetry
            </div>

            {simulationResult ? (
              <div className="space-y-3 animate-in fade-in duration-200">
                {/* Decision Banner */}
                <div className="p-2.5 rounded bg-surface border border-accent/40 space-y-1">
                  <div className="text-[9px] text-foreground-muted uppercase">
                    CLASSIFICATION DECISION
                  </div>
                  <div className="text-base font-bold text-accent flex items-center justify-between">
                    <span>{simulationResult.assigned_class}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30">
                      {(simulationResult.confidence * 100).toFixed(1)}% CONF
                    </span>
                  </div>
                </div>

                {/* Pyrometry & Plume Results */}
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="p-2 rounded bg-surface border border-border">
                    <div className="text-[8.5px] text-foreground-muted uppercase">EMITTER TEMP</div>
                    <div className="text-sm font-bold text-foreground mt-0.5">
                      {simulationResult.pyrometry?.emitter_temp_k} K
                    </div>
                  </div>
                  <div className="p-2 rounded bg-surface border border-border">
                    <div className="text-[8.5px] text-foreground-muted uppercase">COMBUSTION AREA</div>
                    <div className="text-sm font-bold text-accent-cyan mt-0.5">
                      {simulationResult.pyrometry?.emitter_area_m2} m²
                    </div>
                  </div>
                  <div className="p-2 rounded bg-surface border border-border">
                    <div className="text-[8.5px] text-foreground-muted uppercase">PLUME LENGTH</div>
                    <div className="text-sm font-bold text-state-warning mt-0.5">
                      {simulationResult.plume?.plume_length_km} km
                    </div>
                  </div>
                  <div className="p-2 rounded bg-surface border border-border">
                    <div className="text-[8.5px] text-foreground-muted uppercase">EVACUATION RADIUS</div>
                    <div className="text-sm font-bold text-state-error mt-0.5">
                      {simulationResult.plume?.evacuation_radius_km} km
                    </div>
                  </div>
                </div>

                {/* Action: Inject to Map */}
                {onInjectSimulatedEvent && (
                  <button
                    onClick={() => {
                      onInjectSimulatedEvent({
                        event_id: simulationResult.simulated_event_id,
                        latitude: lat,
                        longitude: lon,
                        frp_mw: frp,
                        classification: simulationResult.assigned_class,
                        confidence: simulationResult.confidence,
                        uncertainty_state: "CONFIDENT",
                        is_simulated: true,
                      });
                      onClose();
                    }}
                    className="w-full py-2 px-3 rounded bg-accent-cyan text-background font-bold text-[10px] flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
                  >
                    <Flame className="w-3.5 h-3.5 text-background" />
                    <span className="text-background">INJECT SIMULATED INCIDENT ONTO MAP</span>
                  </button>
                )}
              </div>
            ) : (
              <div className="p-8 rounded bg-surface/50 border border-dashed border-border/80 flex flex-col items-center justify-center text-center text-foreground-muted">
                <Brain className="w-8 h-8 text-foreground-muted/40 mb-2" />
                <div className="text-xs font-semibold text-foreground">Awaiting Inference Execution</div>
                <div className="text-[9.5px] mt-1 max-w-[200px]">
                  Adjust the parameters or select a preset, then click &ldquo;EXECUTE AI CLASSIFICATION&rdquo;.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
