import React, { useState, useMemo } from 'react';
import type { LayerDefinition, LayerCategory } from '../layersConfig';
import { 
  Search, 
  X, 
  ChevronDown, 
  ChevronUp, 
  Info, 
  Satellite, 
  Radio, 
  Building2, 
  Zap, 
  Fuel, 
  ShieldAlert, 
  History, 
  Hospital, 
  Database, 
  Map, 
  Trees,
  Layers as LayersIcon,
  Check
} from 'lucide-react';

interface LayersPanelProps {
  layerDefinitions: LayerDefinition[];
  activeLayers: Record<string, boolean>;
  onToggleLayer: (layerId: string) => void;
  onOpenInfo: (layer: LayerDefinition) => void;
}

export const LayersPanel: React.FC<LayersPanelProps> = ({
  layerDefinitions,
  activeLayers,
  onToggleLayer,
  onOpenInfo,
}) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Filter layers by search query
  const filteredLayers = useMemo(() => {
    if (!searchQuery.trim()) return layerDefinitions;
    const q = searchQuery.toLowerCase();
    return layerDefinitions.filter(l => 
      l.name.toLowerCase().includes(q) ||
      l.subtitle.toLowerCase().includes(q) ||
      l.category.toLowerCase().includes(q) ||
      l.metadata.datasetName.toLowerCase().includes(q) ||
      l.metadata.provider.toLowerCase().includes(q)
    );
  }, [layerDefinitions, searchQuery]);

  // Group filtered layers by category
  const groupedLayers = useMemo(() => {
    const groups: Partial<Record<LayerCategory, LayerDefinition[]>> = {};
    filteredLayers.forEach(l => {
      if (!groups[l.category]) {
        groups[l.category] = [];
      }
      groups[l.category]!.push(l);
    });
    return groups;
  }, [filteredLayers]);

  // Render appropriate domain icon
  const renderIcon = (iconType: LayerDefinition['iconType']) => {
    switch (iconType) {
      case 'satellite':
        return <Satellite className="w-3.5 h-3.5 text-[#10b981]" />;
      case 'radio':
        return <Radio className="w-3.5 h-3.5 text-[#00f0ff] animate-pulse" />;
      case 'factory':
        return <Building2 className="w-3.5 h-3.5 text-[#38bdf8]" />;
      case 'zap':
        return <Zap className="w-3.5 h-3.5 text-[#60a5fa]" />;
      case 'fuel':
        return <Fuel className="w-3.5 h-3.5 text-[#f59e0b]" />;
      case 'anvil':
        return <LayersIcon className="w-3.5 h-3.5 text-[#94a3b8]" />;
      case 'hazard':
        return <ShieldAlert className="w-3.5 h-3.5 text-[#ef4444]" />;
      case 'history':
        return <History className="w-3.5 h-3.5 text-[#f43f5e]" />;
      case 'emergency':
        return <Hospital className="w-3.5 h-3.5 text-[#38bdf8]" />;
      case 'database':
        return <Database className="w-3.5 h-3.5 text-[#a855f7]" />;
      case 'map':
        return <Map className="w-3.5 h-3.5 text-[#64748b]" />;
      case 'trees':
        return <Trees className="w-3.5 h-3.5 text-[#10b981]" />;
      default:
        return <LayersIcon className="w-3.5 h-3.5 text-[#8b92a4]" />;
    }
  };

  const activeCount = Object.values(activeLayers).filter(Boolean).length;

  return (
    <div className="absolute left-4 top-4 z-[400] w-[310px] sm:w-[330px] font-sans">
      <div className="bg-[#0c0d12]/92 backdrop-blur-md border border-[#232836] rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.85)] flex flex-col overflow-hidden transition-all duration-200">
        
        {/* 1. Panel Header (Collapsible) */}
        <div 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="h-10 px-3.5 flex items-center justify-between border-b border-[#1b1e28] cursor-pointer hover:bg-[#14161f] transition-colors select-none"
        >
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold tracking-wider text-white uppercase flex items-center gap-1.5">
              <span>LAYERS</span>
              <span className="text-[10px] font-mono text-[#38bdf8] bg-[#162032] px-1.5 py-0.2 rounded border border-[#233852]">
                {activeCount}/{layerDefinitions.length}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-1 text-[#8b92a4]">
            {isCollapsed ? (
              <ChevronDown className="w-4 h-4 text-[#cbd5e1]" />
            ) : (
              <ChevronUp className="w-4 h-4 text-[#cbd5e1]" />
            )}
          </div>
        </div>

        {/* 2. Expanded Content */}
        {!isCollapsed && (
          <div className="flex flex-col">
            
            {/* Search Box */}
            <div className="p-2.5 border-b border-[#1b1e28]">
              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-2.5 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search layers..."
                  className="w-full bg-[#13151c] border border-[#232836] focus:border-[#38bdf8] focus:bg-[#161822] rounded-lg pl-8 pr-7 py-1.5 text-xs text-[#f3f4f6] placeholder-[#64748b] transition-all outline-none"
                />
                {searchQuery && (
                  <button 
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 text-[#64748b] hover:text-white"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Scrollable Layer List */}
            <div className="max-h-[380px] overflow-y-auto p-1.5 space-y-3 custom-scrollbar">
              {Object.keys(groupedLayers).length === 0 ? (
                <div className="p-6 text-center text-xs text-[#64748b]">
                  No matching layers found
                </div>
              ) : (
                Object.entries(groupedLayers).map(([category, layers]) => (
                  <div key={category} className="space-y-1">
                    
                    {/* Category Label */}
                    <div className="px-2 pt-1 text-[9.5px] font-bold tracking-widest text-[#64748b] uppercase">
                      {category}
                    </div>

                    {/* Layer Items */}
                    <div className="space-y-0.5">
                      {layers?.map((layer) => {
                        const isChecked = !!activeLayers[layer.id];

                        return (
                          <div
                            key={layer.id}
                            className={`flex items-center justify-between p-2 rounded-lg transition-all group border ${
                              isChecked
                                ? 'bg-[#141824] border-[#2b354c]'
                                : 'bg-transparent border-transparent hover:bg-[#131620]'
                            }`}
                          >
                            {/* Left: Checkbox + Icon + Titles */}
                            <div 
                              onClick={() => onToggleLayer(layer.id)}
                              className="flex items-center gap-2.5 flex-1 min-w-0 cursor-pointer pr-1"
                            >
                              {/* Custom Crisp Square Checkbox */}
                              <div className={`w-4 h-4 rounded flex items-center justify-center transition-colors border ${
                                isChecked
                                  ? 'bg-[#0284c7] border-[#38bdf8] text-white shadow-[0_0_8px_rgba(56,189,248,0.4)]'
                                  : 'bg-[#161822] border-[#2d3448] text-transparent hover:border-[#475569]'
                              }`}>
                                <Check className="w-3 h-3 stroke-[3]" />
                              </div>

                              {/* Domain Icon */}
                              <div className="shrink-0">
                                {renderIcon(layer.iconType)}
                              </div>

                              {/* Titles */}
                              <div className="flex flex-col min-w-0 flex-1">
                                <div className="flex items-center gap-1.5">
                                  <span className={`text-[11.5px] font-bold tracking-tight truncate ${
                                    isChecked ? 'text-white' : 'text-[#cbd5e1]'
                                  }`}>
                                    {layer.name}
                                  </span>
                                  <span 
                                    className="text-[9px] font-mono font-medium shrink-0"
                                    style={{ color: layer.statusColor }}
                                  >
                                    ● {layer.status}
                                  </span>
                                </div>
                                <span className="text-[10px] text-[#717d96] truncate font-normal">
                                  {layer.subtitle}
                                </span>
                              </div>
                            </div>

                            {/* Right: Information Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenInfo(layer);
                              }}
                              className="p-1 rounded-full text-[#64748b] hover:text-[#38bdf8] hover:bg-[#1a2030] transition-colors cursor-pointer shrink-0"
                              title={`Inspect ${layer.name} metadata`}
                            >
                              <Info className="w-3.5 h-3.5" />
                            </button>

                          </div>
                        );
                      })}
                    </div>

                  </div>
                ))
              )}
            </div>

            {/* 3. Panel Footer (Reference Image Aesthetic) */}
            <div className="h-8 border-t border-[#1b1e28] px-3 flex items-center justify-between bg-[#0a0b10] text-[10px] text-[#64748b]">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                <span>PyroSat-AI Engine</span>
              </span>
              <span className="font-mono text-[9.5px] text-[#475569]">
                12 DATASETS
              </span>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
