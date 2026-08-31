import React, { useState } from 'react';
import { 
  Flame, 
  Sparkles, 
  X, 
  Crosshair, 
  CheckCircle2, 
  Sliders, 
  Building2, 
  MapPin, 
  Loader2,
  ChevronRight
} from 'lucide-react';

interface PresetScenario {
  name: string;
  category: string;
  lat: number;
  lon: number;
  bright_ti4: number;
  bright_ti5: number;
  frp: number;
  recurrence_90d: number;
  daynight: string;
}

const PRESET_SCENARIOS: PresetScenario[] = [
  {
    name: 'Reliance Jamnagar (Routine Flare Stack)',
    category: 'ROUTINE FLARE',
    lat: 22.3556,
    lon: 69.8653,
    bright_ti4: 375.0,
    bright_ti5: 302.0,
    frp: 35.0,
    recurrence_90d: 0.92,
    daynight: 'N'
  },
  {
    name: 'IOCL Sitapura Depot (Catastrophic Tank Explosion)',
    category: 'INDUSTRIAL DISASTER',
    lat: 26.7925,
    lon: 75.8272,
    bright_ti4: 385.0,
    bright_ti5: 325.0,
    frp: 850.0,
    recurrence_90d: 0.08,
    daynight: 'N'
  },
  {
    name: 'Jim Corbett National Park (Wildfire Canopy Blaze)',
    category: 'WILDFIRE',
    lat: 29.5300,
    lon: 78.7747,
    bright_ti4: 345.0,
    bright_ti5: 310.0,
    frp: 85.0,
    recurrence_90d: 0.02,
    daynight: 'D'
  },
  {
    name: 'Sangrur Punjab (Agricultural Stubble Burning)',
    category: 'AGRO BURNING',
    lat: 30.2458,
    lon: 75.8421,
    bright_ti4: 335.0,
    bright_ti5: 305.0,
    frp: 18.0,
    recurrence_90d: 0.15,
    daynight: 'D'
  },
  {
    name: 'BCCL Jharia Block IV (Coal Seam Smoldering)',
    category: 'COAL SEAM',
    lat: 23.7431,
    lon: 86.4172,
    bright_ti4: 330.0,
    bright_ti5: 312.0,
    frp: 28.0,
    recurrence_90d: 0.88,
    daynight: 'N'
  }
];

interface InteractiveClassifierModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClassifiedEventCreated?: (newEvent: any) => void;
}

export const InteractiveClassifierModal: React.FC<InteractiveClassifierModalProps> = ({
  isOpen,
  onClose,
  onClassifiedEventCreated
}) => {
  const [lat, setLat] = useState<number>(22.3556);
  const [lon, setLon] = useState<number>(69.8653);
  const [ti4, setTi4] = useState<number>(375.0);
  const [ti5, setTi5] = useState<number>(302.0);
  const [frp, setFrp] = useState<number>(35.0);
  const [recurrence, setRecurrence] = useState<number>(0.92);
  const [daynight, setDaynight] = useState<string>('N');

  const [isClassifying, setIsClassifying] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: PresetScenario) => {
    setLat(preset.lat);
    setLon(preset.lon);
    setTi4(preset.bright_ti4);
    setTi5(preset.bright_ti5);
    setFrp(preset.frp);
    setRecurrence(preset.recurrence_90d);
    setDaynight(preset.daynight);
  };

  const handleRunClassification = async () => {
    setIsClassifying(true);
    try {
      const res = await fetch('/api/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: Number(lat),
          longitude: Number(lon),
          bright_ti4: Number(ti4),
          bright_ti5: Number(ti5),
          frp: Number(frp),
          daynight: daynight,
          recurrence_90d: Number(recurrence)
        })
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error('Classification error:', e);
    } finally {
      setIsClassifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-[#0c0e14] border border-[#222838] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-100">
        
        {/* Header */}
        <div className="p-4 bg-gradient-to-r from-slate-950 via-[#101420] to-slate-950 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                Live Anomaly Classification & Pyrometry Lab
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Dozier + Multi-Modal AI
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Test custom satellite telemetry or select historical benchmarks for real-time inference.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left Column: Input Parameters & Presets (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            
            {/* Presets Row */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Quick Benchmark Presets
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {PRESET_SCENARIOS.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleApplyPreset(p)}
                    className="p-2 text-left bg-[#131722] hover:bg-[#1b2130] border border-slate-800 hover:border-indigo-500/50 rounded-lg transition-all text-xs"
                  >
                    <div className="font-semibold text-slate-200 truncate">{p.name}</div>
                    <div className="text-[10px] text-indigo-400 font-mono mt-0.5">{p.category}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Coordinates */}
            <div className="bg-[#121520] p-3 rounded-xl border border-slate-800/80 space-y-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-indigo-400" />
                Geospatial Coordinates
              </span>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10.5px] text-slate-400 block">Latitude (°N)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lat}
                    onChange={(e) => setLat(parseFloat(e.target.value))}
                    className="w-full bg-[#181c2b] border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-[10.5px] text-slate-400 block">Longitude (°E)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lon}
                    onChange={(e) => setLon(parseFloat(e.target.value))}
                    className="w-full bg-[#181c2b] border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Radiometric Inversion Inputs */}
            <div className="bg-[#121520] p-3.5 rounded-xl border border-slate-800/80 space-y-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-400" />
                VIIRS 375m Radiometric Telemetry
              </span>

              {/* MWIR TI4 Slider */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">VIIRS Band I4 MWIR (3.74µm)</span>
                  <span className="font-mono text-amber-400 font-bold">{ti4} K</span>
                </div>
                <input
                  type="range"
                  min="290"
                  max="390"
                  step="1"
                  value={ti4}
                  onChange={(e) => setTi4(parseFloat(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>

              {/* LWIR TI5 Slider */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">VIIRS Band I5 LWIR (11.45µm)</span>
                  <span className="font-mono text-cyan-400 font-bold">{ti5} K</span>
                </div>
                <input
                  type="range"
                  min="270"
                  max="350"
                  step="1"
                  value={ti5}
                  onChange={(e) => setTi5(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              {/* FRP Slider */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">Fire Radiative Power (FRP)</span>
                  <span className="font-mono text-rose-400 font-bold">{frp} MW</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="900"
                  step="1"
                  value={frp}
                  onChange={(e) => setFrp(parseFloat(e.target.value))}
                  className="w-full accent-rose-500 cursor-pointer"
                />
              </div>

              {/* 90-Day Recurrence */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">90-Day Thermal Recurrence Index</span>
                  <span className="font-mono text-emerald-400 font-bold">{(recurrence * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.01"
                  value={recurrence}
                  onChange={(e) => setRecurrence(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
              </div>
            </div>

            {/* Execute Button */}
            <button
              onClick={handleRunClassification}
              disabled={isClassifying}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 active:scale-[0.99] text-white font-bold text-xs shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              {isClassifying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Computing Dozier Inversion & AI Classifier...</span>
                </>
              ) : (
                <>
                  <Flame className="w-4 h-4 text-amber-300" />
                  <span>Run Real-Time AI Classification & Pyrometry</span>
                </>
              )}
            </button>
          </div>

          {/* Right Column: Live Inferred Intelligence (5 cols) */}
          <div className="lg:col-span-5 bg-[#10131d] border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Model Prediction & Output
                </span>
                {result && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {result.classification.confidence_score.toFixed(1)}% Confidence
                  </span>
                )}
              </div>

              {result ? (
                <div className="mt-3 space-y-3">
                  {/* Class Badge */}
                  <div 
                    className="p-3 rounded-xl border flex items-center gap-2.5"
                    style={{ 
                      backgroundColor: `${result.classification.color}15`,
                      borderColor: `${result.classification.color}40`
                    }}
                  >
                    <div 
                      className="w-3.5 h-3.5 rounded-full animate-pulse shrink-0"
                      style={{ backgroundColor: result.classification.color }}
                    />
                    <div>
                      <span className="text-xs font-bold block" style={{ color: result.classification.color }}>
                        {result.classification.predicted_class_name}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        Calibrated Band: {result.classification.confidence_band}
                      </span>
                    </div>
                  </div>

                  {/* Dozier Pyrometry Inversion */}
                  <div className="grid grid-cols-2 gap-2 bg-[#161a27] p-2.5 rounded-lg border border-slate-800 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-400">Flame Temp (T_flame)</div>
                      <div className="font-mono font-bold text-amber-400 mt-0.5">
                        {result.physical_characterization.estimated_emitter_temp_k.toFixed(0)} K
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400">Sub-Pixel Fire Area</div>
                      <div className="font-mono font-bold text-cyan-400 mt-0.5">
                        {result.physical_characterization.estimated_emitter_area_m2.toFixed(1)} m²
                      </div>
                    </div>
                  </div>

                  {/* Spatial Context */}
                  <div className="bg-[#161a27] p-2.5 rounded-lg border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <Building2 className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="font-semibold truncate">{result.spatial_attribution.nearest_facility}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Distance: {result.spatial_attribution.dist_km.toFixed(2)} km</span>
                      <span>LULC: {result.spatial_attribution.dominant_lulc}</span>
                    </div>
                  </div>

                  {/* Top SHAP Signals */}
                  <div className="space-y-1.5">
                    <span className="text-[10.5px] font-bold text-slate-400 block">
                      Top Decisive Signals
                    </span>
                    {result.explainability_evidence?.positive_signals?.slice(0, 3).map((sig: string, i: number) => (
                      <div key={i} className="flex items-start gap-1.5 text-[10.5px] text-emerald-300">
                        <CheckCircle2 className="w-3 h-3 shrink-0 mt-0.5 text-emerald-400" />
                        <span>{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center space-y-2">
                  <Crosshair className="w-8 h-8 text-slate-600 mx-auto animate-pulse" />
                  <p className="text-xs text-slate-400">
                    Adjust telemetry parameters on the left and click <strong>Run Real-Time AI Classification</strong> to see live inference.
                  </p>
                </div>
              )}
            </div>

            {/* Action Footer */}
            {result && (
              <button
                onClick={() => {
                  if (onClassifiedEventCreated) {
                    onClassifiedEventCreated(result);
                  }
                  onClose();
                }}
                className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/30"
              >
                <span>Pin Classified Anomaly to Map</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
