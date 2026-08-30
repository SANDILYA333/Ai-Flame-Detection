import React from 'react';
import type { LayerDefinition } from '../layersConfig';
import { X, Database, Globe2, Satellite, Layers, ShieldCheck, Calendar } from 'lucide-react';

interface LayerInfoModalProps {
  layer: LayerDefinition | null;
  onClose: () => void;
}

export const LayerInfoModal: React.FC<LayerInfoModalProps> = ({ layer, onClose }) => {
  if (!layer) return null;

  const m = layer.metadata;

  return (
    <div className="fixed inset-0 z-[1000] bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-[#0e1017] border border-[#262b3a] rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-120 text-[#f3f4f6] font-sans">
        
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-[#1f232e]">
          <div className="flex items-center gap-3">
            <div 
              className="p-2 rounded-xl border flex items-center justify-center"
              style={{ borderColor: `${layer.statusColor}40`, backgroundColor: `${layer.statusColor}15` }}
            >
              <Database className="w-5 h-5" style={{ color: layer.statusColor }} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold tracking-tight text-white uppercase">
                  {layer.name}
                </h3>
                <span 
                  className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border"
                  style={{ 
                    color: layer.statusColor, 
                    borderColor: `${layer.statusColor}40`, 
                    backgroundColor: `${layer.statusColor}15` 
                  }}
                >
                  ● {layer.status}
                </span>
              </div>
              <div className="text-xs text-[#8b92a4] mt-0.5 font-medium">
                {layer.subtitle}
              </div>
            </div>
          </div>

          <button 
            onClick={onClose}
            className="p-1 rounded-lg text-[#64748b] hover:text-white hover:bg-[#161922] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Dataset Description */}
        <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] text-xs text-[#cbd5e1] leading-relaxed">
          {m.description || 'Metadata not configured'}
        </div>

        {/* Structured Provenance Grid */}
        <div className="grid grid-cols-2 gap-2.5 text-xs">
          
          {/* Full Dataset Name */}
          <div className="col-span-2 bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider flex items-center gap-1.5">
              <Layers className="w-3 h-3 text-[#38bdf8]" />
              <span>OFFICIAL DATASET TITLE</span>
            </div>
            <div className="text-xs font-semibold text-[#f3f4f6]">
              {m.datasetName || 'Metadata not configured'}
            </div>
          </div>

          {/* Provider / Source */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-[#10b981]" />
              <span>PROVIDER / AUTHORITY</span>
            </div>
            <div className="text-xs font-medium text-[#e2e8f0]">
              {m.provider || 'Metadata not configured'}
            </div>
          </div>

          {/* Satellites & Sensors / Resolution */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider flex items-center gap-1.5">
              <Satellite className="w-3 h-3 text-[#f59e0b]" />
              <span>SENSOR & RESOLUTION</span>
            </div>
            <div className="text-xs font-medium text-[#e2e8f0]">
              {m.sensor ? `${m.sensor} (${m.resolution})` : m.resolution || 'Metadata not configured'}
            </div>
          </div>

          {/* Data Type */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider">
              DATA TYPE & FORMAT
            </div>
            <div className="text-xs font-medium text-[#cbd5e1]">
              {m.dataType || 'Metadata not configured'}
            </div>
          </div>

          {/* Geographic Coverage */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider flex items-center gap-1.5">
              <Globe2 className="w-3 h-3 text-[#38bdf8]" />
              <span>SPATIAL COVERAGE</span>
            </div>
            <div className="text-xs font-medium text-[#cbd5e1]">
              {m.coverage || 'Metadata not configured'}
            </div>
          </div>

          {/* Ingestion Mode */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider flex items-center gap-1.5">
              <Calendar className="w-3 h-3 text-[#a855f7]" />
              <span>INGESTION MODE & RECURRENCE</span>
            </div>
            <div className="text-xs font-medium text-[#cbd5e1]">
              {m.mode || 'Metadata not configured'}
            </div>
          </div>

          {/* Record Count / Archive Volume */}
          <div className="bg-[#13151c] p-3 rounded-xl border border-[#1f232e] space-y-1">
            <div className="text-[10px] uppercase font-bold text-[#64748b] tracking-wider">
              CORPUS SCALE
            </div>
            <div className="text-xs font-mono font-medium text-[#38bdf8]">
              {m.recordCount || 'Configured in System'}
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-[#1f232e] text-xs">
          <span className="text-[11px] text-[#64748b] flex items-center gap-1">
            <span>Source:</span>
            <span className="text-[#8b92a4] font-mono">{m.source}</span>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-[#1f2433] hover:bg-[#282f42] border border-[#2d3546] text-xs font-semibold text-white transition-colors"
          >
            Close Inspector
          </button>
        </div>

      </div>
    </div>
  );
};
