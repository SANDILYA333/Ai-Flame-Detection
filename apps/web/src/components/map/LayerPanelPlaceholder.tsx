"use client";

import React, { useState } from "react";
import { Layers, Flame, Factory, Trees, RotateCw, AlertTriangle, Building2, Search } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { Toggle } from "@/components/ui/Toggle";
import { Badge } from "@/components/ui/Badge";
import { INITIAL_LAYERS } from "@/config/ui";
import { useEventContext } from "@/context/EventContext";
import { cn } from "@/lib/utils";

export interface LayerPanelProps {
  onClose?: () => void;
  className?: string;
}

export function LayerPanelPlaceholder({ onClose, className }: LayerPanelProps) {
  const { activeLayers, toggleLayer } = useEventContext();
  const [searchQuery, setSearchQuery] = useState("");

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "Flame":
        return <Flame className="w-3.5 h-3.5 text-thermal-primary" />;
      case "Factory":
        return <Factory className="w-3.5 h-3.5 text-accent" />;
      case "Trees":
        return <Trees className="w-3.5 h-3.5 text-state-warning" />;
      case "RotateCw":
        return <RotateCw className="w-3.5 h-3.5 text-accent-cyan" />;
      case "AlertTriangle":
        return <AlertTriangle className="w-3.5 h-3.5 text-state-error" />;
      case "Building2":
        return <Building2 className="w-3.5 h-3.5 text-foreground-muted" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-foreground-muted" />;
    }
  };

  const filteredLayers = INITIAL_LAYERS.filter((layer) =>
    layer.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeCount = Object.values(activeLayers).filter(Boolean).length;

  return (
    <Panel
      variant="glass"
      className={cn("w-72 max-h-[80vh] flex flex-col p-3 shadow-panel select-none", className)}
    >
      <PanelHeader
        title="GIS Layers"
        subtitle="Operational Overlay Filter"
        icon={<Layers className="w-4 h-4 text-accent-cyan" />}
        onClose={onClose}
      />

      {/* Layer search */}
      <div className="relative mb-2.5">
        <Search className="absolute left-2 w-3 h-3 text-foreground-muted pointer-events-none top-2.5" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter layers..."
          className="w-full h-7 pl-7 pr-2 text-[11px] bg-surface-raised border border-border rounded-control text-foreground placeholder:text-foreground-disabled focus:outline-none focus:border-accent"
        />
      </div>

      {/* Layers list */}
      <div className="space-y-1 overflow-y-auto pr-1">
        {filteredLayers.map((layer) => {
          const isEnabled = activeLayers[layer.id] ?? layer.enabled;

          return (
            <div
              key={layer.id}
              className={cn(
                "flex items-center justify-between p-2 rounded-control border transition-all duration-150",
                isEnabled
                  ? "bg-surface-raised/70 border-border/80 text-foreground"
                  : "bg-surface/30 border-transparent text-foreground-muted hover:bg-surface-hover/50"
              )}
            >
              <div className="flex items-center gap-2 min-w-0 pr-2">
                <span className="shrink-0">{getIcon(layer.icon)}</span>
                <div className="min-w-0">
                  <div className="text-[11px] font-medium leading-tight truncate">
                    {layer.label}
                  </div>
                  <div className="text-[9px] text-foreground-muted truncate font-mono">
                    {layer.description}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
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

      {/* Footer status */}
      <div className="mt-2.5 pt-2 border-t border-border/60 flex items-center justify-between text-[10px] text-foreground-muted font-mono">
        <span>Active Overlays:</span>
        <Badge variant="success" size="sm">
          {activeCount} of {INITIAL_LAYERS.length}
        </Badge>
      </div>
    </Panel>
  );
}
