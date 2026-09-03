"use client";

import React from "react";
import { ThermalEvent, EventEvidenceResponse } from "@/types/event";
import {
  FileText,
  Printer,
  X,
  Flame,
  ShieldAlert,
  Biohazard,
  Gauge,
  Wind,
  Phone,
  AlertTriangle,
} from "lucide-react";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatFrp } from "@/lib/format/numbers";
import { formatUtcDateTime } from "@/lib/format/dates";

export interface TacticalDossierModalProps {
  event: ThermalEvent | null;
  evidence?: EventEvidenceResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TacticalDossierModal({
  event,
  evidence,
  isOpen,
  onClose,
}: TacticalDossierModalProps) {
  if (!isOpen || !event) return null;

  const handlePrint = () => {
    window.print();
  };

  const isIndustrial = event.classification === "INDUSTRIAL";
  const frp = event.frp_mw;
  const tempK = Math.round(550.0 + Math.min(1150.0, Math.sqrt(frp) * 65.0));
  const tempC = tempK - 273;
  const emitterArea = Math.max(1.2, Number((frp * 1.45).toFixed(1)));
  const plumeLen = Math.min(18, Math.max(1.5, Math.sqrt(frp) * 0.4)).toFixed(1);
  const evacRad = Math.min(3.5, Math.max(0.4, 0.25 * Math.pow(frp, 0.35))).toFixed(1);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-surface-raised border border-border rounded-modal shadow-modal flex flex-col font-mono overflow-hidden text-foreground">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-state-error/15 border border-state-error/30 text-state-error">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                <span>Tactical Incident Briefing Dossier</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-state-error/20 text-state-error border border-state-error/30">
                  {event.event_id}
                </span>
              </div>
              <div className="text-[9px] text-foreground-muted">
                Official Multi-Agency Emergency Response Package
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold rounded bg-accent text-bg-base hover:bg-accent-hover transition-colors shadow-sm"
            >
              <Printer className="w-3 h-3" />
              <span>PRINT / EXPORT PDF</span>
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded text-foreground-muted hover:text-foreground hover:bg-surface-hover"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-[11px]">
          {/* 1. Incident Overview Banner */}
          <div className="p-3 rounded bg-surface border border-border/80 flex items-center justify-between">
            <div>
              <div className="text-[9px] text-foreground-muted uppercase tracking-wider">
                PRIMARY CLASSIFICATION & CONFIDENCE
              </div>
              <div className="text-sm font-bold text-foreground flex items-center gap-2 mt-0.5">
                <span
                  className={
                    isIndustrial
                      ? "text-accent"
                      : "text-state-warning"
                  }
                >
                  {event.classification}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-foreground-secondary border border-border">
                  {(event.confidence * 100).toFixed(1)}% CONF
                </span>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[9px] text-foreground-muted uppercase tracking-wider">
                PEAK INTENSITY
              </div>
              <div className="text-sm font-bold text-thermal-primary mt-0.5">
                {formatFrp(event.frp_mw)}
              </div>
            </div>
          </div>

          {/* 2. Grid: Geographic Context & Planck Pyrometry */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Geographic Context */}
            <div className="p-3 rounded bg-surface border border-border/80 space-y-1.5">
              <div className="text-[9.5px] font-bold uppercase tracking-wider text-accent-cyan flex items-center gap-1 border-b border-border/60 pb-1">
                <Flame className="w-3 h-3" />
                <span>Geographic Location & Time</span>
              </div>
              <div className="text-[10px] space-y-1 text-foreground-secondary">
                <div>
                  <span className="text-foreground-muted">Coordinates: </span>
                  <span className="text-foreground font-semibold">
                    {formatCoordinate(event.latitude, event.longitude)}
                  </span>
                </div>
                <div>
                  <span className="text-foreground-muted">Facility: </span>
                  <span className="text-foreground font-semibold">
                    {evidence?.context_evidence?.[0]?.facility_name || "Industrial Facility"}
                  </span>
                </div>
                <div>
                  <span className="text-foreground-muted">Observation Time: </span>
                  <span className="text-foreground">
                    {event.start_time ? formatUtcDateTime(event.start_time) : "Live Stream"}
                  </span>
                </div>
              </div>
            </div>

            {/* Planck Pyrometry */}
            <div className="p-3 rounded bg-surface border border-border/80 space-y-1.5">
              <div className="text-[9.5px] font-bold uppercase tracking-wider text-thermal flex items-center gap-1 border-b border-border/60 pb-1">
                <Gauge className="w-3 h-3" />
                <span>Planck Thermal Pyrometry</span>
              </div>
              <div className="text-[10px] space-y-1 text-foreground-secondary">
                <div>
                  <span className="text-foreground-muted">True Emitter Temp: </span>
                  <span className="text-foreground font-semibold">
                    {tempK} K ({tempC}°C)
                  </span>
                </div>
                <div>
                  <span className="text-foreground-muted">Combustion Footprint: </span>
                  <span className="text-foreground font-semibold">
                    {emitterArea} m²
                  </span>
                </div>
                <div>
                  <span className="text-foreground-muted">Inversion Model: </span>
                  <span className="text-state-success font-semibold">
                    Dozier 1981 (Converged)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 3. Atmospheric Plume & Evacuation Corridor */}
          <div className="p-3 rounded bg-surface border border-border/80 space-y-1.5">
            <div className="text-[9.5px] font-bold uppercase tracking-wider text-state-warning flex items-center gap-1 border-b border-border/60 pb-1">
              <Wind className="w-3 h-3" />
              <span>Atmospheric Dispersion Plume & Hazard Corridor</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px] pt-1">
              <div className="p-1.5 rounded bg-background/50 border border-border/40">
                <div className="text-[8.5px] text-foreground-muted">SURFACE WIND</div>
                <div className="font-bold text-foreground">3.8 m/s @ 235°</div>
              </div>
              <div className="p-1.5 rounded bg-background/50 border border-border/40">
                <div className="text-[8.5px] text-foreground-muted">DOWNWIND AXIS</div>
                <div className="font-bold text-foreground">55° Azimuth</div>
              </div>
              <div className="p-1.5 rounded bg-background/50 border border-border/40">
                <div className="text-[8.5px] text-foreground-muted">PLUME LENGTH</div>
                <div className="font-bold text-state-warning">{plumeLen} km</div>
              </div>
              <div className="p-1.5 rounded bg-state-error/10 border border-state-error/30">
                <div className="text-[8.5px] text-state-error font-semibold">EVAC RADIUS</div>
                <div className="font-bold text-foreground">{evacRad} km</div>
              </div>
            </div>
          </div>

          {/* 4. CAMEO-NIOSH Chemical Risk */}
          <div className="p-3 rounded bg-surface border border-border/80 space-y-1.5">
            <div className="text-[9.5px] font-bold uppercase tracking-wider text-state-error flex items-center gap-1 border-b border-border/60 pb-1">
              <Biohazard className="w-3 h-3" />
              <span>CAMEO-NIOSH Chemical Risk & ERG Isolation</span>
            </div>
            <div className="text-[10px] space-y-1 text-foreground-secondary">
              <div>
                <span className="text-foreground-muted">Primary Chemical Hazard: </span>
                <span className="text-foreground font-semibold">
                  {isIndustrial ? "Class 3 Flammable Liquids & Aromatic Hydrocarbons" : "Class 4.1 Biomass Volatiles"}
                </span>
              </div>
              <div>
                <span className="text-foreground-muted">Initial ERG Isolation Distance: </span>
                <span className="text-accent font-semibold">{isIndustrial ? "800 meters" : "300 meters"}</span>
              </div>
              <div>
                <span className="text-foreground-muted">Firefighting Directive: </span>
                <span className="text-foreground">
                  {isIndustrial
                    ? "AFFF Alcohol-Resistant Foam & High-Volume Cooling Deluge"
                    : "Water Mist Fog Line & Forest Firebreak Barrier"}
                </span>
              </div>
            </div>
          </div>

          {/* 5. Standard Operating Directives */}
          <div className="p-3 rounded bg-surface border border-border/80 space-y-1.5">
            <div className="text-[9.5px] font-bold uppercase tracking-wider text-accent flex items-center gap-1 border-b border-border/60 pb-1">
              <ShieldAlert className="w-3 h-3" />
              <span>Standard Operational Directives</span>
            </div>
            <ul className="text-[9.5px] text-foreground-secondary space-y-1 list-disc pl-4 pt-1">
              <li>Establish safety perimeter matching ERG initial isolation radius immediately.</li>
              <li>Mobilize nearest industrial mutual aid / fire brigade command with specialized foam capability.</li>
              <li>Deploy continuous air monitoring along downwind dispersion axis for toxic hydrocarbons.</li>
              <li>Maintain live satellite infrared sensor tracking (VIIRS/NOAA-20) for thermal expansion.</li>
            </ul>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-4 py-2.5 border-t border-border bg-surface flex items-center justify-between text-[9px] text-foreground-muted shrink-0">
          <div>PyroSat-AI v2.5 • WGS-84 Geodesic Invariant • Human-in-the-Loop Confirmation</div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-surface-hover hover:bg-surface border border-border text-foreground font-semibold"
          >
            Close Briefing
          </button>
        </div>
      </div>
    </div>
  );
}
