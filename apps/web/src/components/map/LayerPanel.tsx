"use client";

import React, { useState } from "react";
import {
  Layers,
  Flame,
  Factory,
  Trees,
  RotateCw,
  AlertTriangle,
  Building2,
  Search,
  CheckCheck,
  RotateCcw,
  Sparkles,
  Info,
  Radio,
  Zap,
  ShieldAlert,
  Map as MapIcon,
} from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { Toggle } from "@/components/ui/Toggle";
import { Badge } from "@/components/ui/Badge";
import { INITIAL_LAYERS } from "@/config/ui";
import { useEventContext } from "@/context/EventContext";
import { GisLayerItem } from "@/types/layer";
import { LayerMetadataModal } from "./LayerMetadataModal";
import { cn } from "@/lib/utils";

export interface LayerPanelProps {
  onClose?: () => void;
  className?: string;
}

export function LayerPanel({ onClose, className }: LayerPanelProps) {
  const { activeLayers, toggleLayer, stats, resetFilters } = useEventContext();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLayerForModal, setSelectedLayerForModal] = useState<GisLayerItem | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const getLayerIcon = (layerId: string) => {
    switch (layerId) {
      case "nasa-firms-viirs":
      case "all_thermal":
        return <Flame className="w-3.5 h-3.5 text-thermal-primary" />;
      case "nasa-firms-live-api":
        return <Radio className="w-3.5 h-3.5 text-thermal" />;
      case "india-industrial-facilities":
      case "industrial":
        return <Factory className="w-3.5 h-3.5 text-accent" />;
      case "global-power-plants":
        return <Zap className="w-3.5 h-3.5 text-state-warning" />;
      case "global-oil-gas-tracker":
        return <Flame className="w-3.5 h-3.5 text-state-warning" />;
      case "global-iron-steel-tracker":
        return <Building2 className="w-3.5 h-3.5 text-accent-cyan" />;
      case "cameo-niosh-hazmat":
        return <AlertTriangle className="w-3.5 h-3.5 text-state-error" />;
      case "historical-disasters":
        return <RotateCw className="w-3.5 h-3.5 text-state-error" />;
      case "india-emergency-services":
        return <ShieldAlert className="w-3.5 h-3.5 text-accent-cyan" />;
      case "multimodal-benchmark":
        return <Layers className="w-3.5 h-3.5 text-foreground-muted" />;
      case "india-boundaries":
        return <MapIcon className="w-3.5 h-3.5 text-foreground-muted" />;
      case "indian-forest-reserves":
      case "non_industrial":
        return <Trees className="w-3.5 h-3.5 text-state-success" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-foreground-muted" />;
    }
  };

  const filteredLayers = INITIAL_LAYERS.filter(
    (layer) =>
      layer.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      layer.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      layer.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeCount = Object.values(activeLayers).filter(Boolean).length;

  return (
    <>
      <Panel
        variant="glass"
        className={cn(
          "w-88 flex flex-col p-3 shadow-panel select-none font-mono transition-all duration-200",
          !isCollapsed && "max-h-[85vh]",
          className
        )}
      >
        <PanelHeader
          title="12 GIS Layers"
          subtitle="Operational Intelligence Catalog"
          icon={<Layers className="w-4 h-4 text-accent-cyan" />}
          onClose={onClose}
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        />

        {!isCollapsed && (
          <>
            {/* Layer Search Input */}
            <div className="relative mb-2.5">
              <Search className="absolute left-2.5 w-3 h-3 text-foreground-muted pointer-events-none top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search all 12 GIS layers..."
                className="w-full h-7 pl-7 pr-2 text-[11px] bg-surface-raised border border-border rounded-control text-foreground placeholder:text-foreground-muted/60 focus:outline-none focus:border-accent"
              />
            </div>

            {/* Quick Action Buttons */}
            <div className="flex items-center gap-1.5 mb-2.5">
              <button
                onClick={() => {
                  INITIAL_LAYERS.forEach((l) => {
                    if (!activeLayers[l.id]) toggleLayer(l.id);
                  });
                }}
                className="flex-1 h-6 px-2 text-[9px] font-semibold rounded-control bg-surface hover:bg-surface-raised border border-border/80 text-foreground-secondary hover:text-foreground transition-colors flex items-center justify-center gap-1"
              >
                <CheckCheck className="w-2.5 h-2.5 text-accent" />
                <span>Enable All</span>
              </button>
              <button
                onClick={() => {
                  INITIAL_LAYERS.forEach((l) => {
                    const shouldBeOn =
                      l.id === "nasa-firms-viirs" ||
                      l.id === "india-industrial-facilities" ||
                      l.id === "cameo-niosh-hazmat" ||
                      l.id === "india-emergency-services";
                    if (Boolean(activeLayers[l.id]) !== shouldBeOn) toggleLayer(l.id);
                  });
                }}
                className="flex-1 h-6 px-2 text-[9px] font-semibold rounded-control bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent transition-colors flex items-center justify-center gap-1"
              >
                <Sparkles className="w-2.5 h-2.5 text-accent" />
                <span>Tactical Core</span>
              </button>
              <button
                onClick={resetFilters}
                title="Reset to default layers"
                className="h-6 px-2 text-[9px] font-semibold rounded-control bg-surface hover:bg-surface-raised border border-border/80 text-foreground-muted hover:text-foreground transition-colors flex items-center justify-center"
              >
                <RotateCcw className="w-2.5 h-2.5" />
              </button>
            </div>

            {/* Layers List */}
            <div className="space-y-1.5 overflow-y-auto pr-1 flex-1 max-h-[55vh] scrollbar-thin">
              {filteredLayers.map((layer) => {
                const isEnabled = activeLayers[layer.id] ?? layer.enabled;
                const icon = getLayerIcon(layer.id);

                return (
                  <div
                    key={layer.id}
                    className={cn(
                      "flex items-center justify-between p-2 rounded-control border transition-all duration-150",
                      isEnabled
                        ? "bg-surface-raised/80 border-border text-foreground"
                        : "bg-surface/30 border-transparent text-foreground-muted hover:bg-surface-hover/50"
                    )}
                  >
                    <div className="flex items-center gap-2 min-w-0 pr-2">
                      <span className="shrink-0">{icon}</span>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10.5px] font-semibold leading-tight truncate">
                            {layer.label}
                          </span>
                          <span className="text-[8px] px-1 py-0.2 rounded bg-surface border border-border text-foreground-muted uppercase font-bold shrink-0">
                            {layer.category}
                          </span>
                        </div>
                        <div className="text-[8.5px] text-foreground-muted truncate font-mono mt-0.5">
                          {layer.description}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => setSelectedLayerForModal(layer)}
                        title="View Layer Provenance & Interpretation"
                        className="p-1 rounded text-foreground-muted hover:text-accent-cyan hover:bg-surface-hover transition-colors"
                      >
                        <Info className="w-3.5 h-3.5" />
                      </button>
                      <Toggle
                        size="sm"
                        checked={isEnabled}
                        onChange={() => toggleLayer(layer.id)}
                        ariaLabel={`Toggle ${layer.label}`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer Status */}
            <div className="mt-2.5 pt-2 border-t border-border/60 flex items-center justify-between text-[10px] text-foreground-muted font-mono">
              <span>Active Overlays:</span>
              <Badge variant={activeCount > 0 ? "success" : "neutral"} size="sm">
                {activeCount} of {INITIAL_LAYERS.length} ACTIVE
              </Badge>
            </div>
          </>
        )}
      </Panel>

      <LayerMetadataModal
        layer={selectedLayerForModal}
        isOpen={Boolean(selectedLayerForModal)}
        onClose={() => setSelectedLayerForModal(null)}
      />
    </>
  );
}

export { LayerPanel as LayerPanelPlaceholder };
