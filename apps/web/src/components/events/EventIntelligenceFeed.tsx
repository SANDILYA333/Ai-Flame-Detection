"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  Radio,
  RotateCw,
  Search,
  Cpu,
  Clock,
  FilterX,
} from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { Badge } from "@/components/ui/Badge";
import { EventCard } from "./EventCard";
import { ThermalEvent } from "@/types/event";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import { useEventContext } from "@/context/EventContext";
import { APP_CONFIG } from "@/config/ui";
import { cn } from "@/lib/utils";

export type EventSortOption = "newest" | "risk" | "frp" | "confidence" | "detections";

export interface EventIntelligenceFeedProps {
  events?: ThermalEvent[];
  selectedEvent?: ThermalEvent | null;
  onSelectEvent?: (event: ThermalEvent) => void;
  onClose?: () => void;
  className?: string;
}

export function EventIntelligenceFeed({
  events: propEvents,
  selectedEvent: propSelectedEvent,
  onSelectEvent,
  onClose,
  className,
}: EventIntelligenceFeedProps) {
  const {
    filteredEvents: contextEvents,
    selectedEvent: contextSelectedEvent,
    setSelectedEvent,
    stats,
    isLiveBackend,
    isLoading,
    isFetching,
    refetch,
    searchQuery,
    setSearchQuery,
    resetFilters,
  } = useEventContext();

  const events = propEvents || contextEvents;
  const selectedEvent = propSelectedEvent !== undefined ? propSelectedEvent : contextSelectedEvent;

  const [sortOption, setSortOption] = useState<EventSortOption>("newest");
  const listContainerRef = useRef<HTMLDivElement>(null);

  // Sort events based on selected sort option
  const sortedEvents = useMemo(() => {
    const list = [...events];
    switch (sortOption) {
      case "risk":
        return list.sort((a, b) => {
          const riskA = calculateOperationalRisk(a).score;
          const riskB = calculateOperationalRisk(b).score;
          return riskB - riskA;
        });
      case "frp":
        return list.sort((a, b) => b.frp_mw - a.frp_mw);
      case "confidence":
        return list.sort((a, b) => b.confidence - a.confidence);
      case "detections":
        return list.sort((a, b) => b.detection_count - a.detection_count);
      case "newest":
      default:
        return list.sort((a, b) => {
          const timeA = new Date(a.start_time).getTime() || 0;
          const timeB = new Date(b.start_time).getTime() || 0;
          return timeB - timeA;
        });
    }
  }, [events, sortOption]);

  // Handle event selection
  const handleSelect = (event: ThermalEvent) => {
    if (onSelectEvent) {
      onSelectEvent(event);
    } else {
      setSelectedEvent(event);
    }
  };

  return (
    <Panel
      variant="glass"
      className={cn(
        "w-96 max-h-[88vh] flex flex-col p-3 shadow-panel select-none font-mono",
        className
      )}
    >
      {/* 1. Feed Header with Live Ingestion & Refresh Trigger */}
      <div className="flex items-center justify-between border-b border-border/80 pb-2.5 mb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-control bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
          </div>
          <div>
            <div className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <span>LIVE INTELLIGENCE</span>
              <Badge variant="thermal" size="sm" className="text-[9px] py-0">
                {events.length} ACTIVE
              </Badge>
            </div>
            <div className="text-[10px] text-foreground-muted">
              {isLiveBackend ? "FastAPI Ingestion Active" : "Multi-Source Telemetry"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh event stream"
            className="p-1.5 rounded-control bg-surface hover:bg-surface-raised border border-border text-foreground-muted hover:text-foreground transition-colors disabled:opacity-50"
          >
            <RotateCw className={cn("w-3.5 h-3.5", isFetching && "animate-spin text-accent")} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              title="Close Intelligence Feed"
              className="p-1.5 rounded-control bg-surface hover:bg-surface-raised border border-border text-foreground-muted hover:text-foreground transition-colors text-xs font-semibold px-2"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 2. Aggregate KPI Quick Counters */}
      <div className="grid grid-cols-4 gap-1.5 mb-2.5 text-[10px]">
        <div className="p-1.5 rounded bg-surface/80 border border-border text-center">
          <div className="text-foreground-muted text-[9px]">TOTAL</div>
          <div className="font-bold text-foreground">{stats.total}</div>
        </div>
        <div className="p-1.5 rounded bg-surface/80 border border-border text-center">
          <div className="text-accent text-[9px]">IND</div>
          <div className="font-bold text-accent">{stats.industrial}</div>
        </div>
        <div className="p-1.5 rounded bg-surface/80 border border-border text-center">
          <div className="text-state-warning text-[9px]">REVIEW</div>
          <div className="font-bold text-state-warning">{stats.reviewRequired}</div>
        </div>
        <div className="p-1.5 rounded bg-surface/80 border border-border text-center">
          <div className="text-accent-cyan text-[9px]">UNK</div>
          <div className="font-bold text-accent-cyan">{stats.unknown}</div>
        </div>
      </div>

      {/* 3. Search & Sort Controls Strip */}
      <div className="flex items-center gap-1.5 mb-2">
        <div className="relative flex-1">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-foreground-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search feed / location..."
            className="w-full h-7 pl-6 pr-2 bg-background/70 border border-border rounded-control text-[11px] text-foreground placeholder:text-foreground-muted/60 focus:outline-none focus:border-accent"
          />
        </div>

        <div className="relative">
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value as EventSortOption)}
            className="h-7 px-2 bg-surface border border-border rounded-control text-[10px] text-foreground-secondary hover:text-foreground focus:outline-none focus:border-accent cursor-pointer"
          >
            <option value="newest">Newest</option>
            <option value="risk">Max Risk</option>
            <option value="frp">Max FRP</option>
            <option value="confidence">Confidence</option>
            <option value="detections">Detections</option>
          </select>
        </div>
      </div>

      {/* 4. Scrollable Event Card Stream */}
      <div
        ref={listContainerRef}
        className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[220px] max-h-[52vh] scrollbar-thin"
      >
        {isLoading && events.length === 0 ? (
          <div className="space-y-2 py-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 rounded-control bg-surface/50 border border-border/40 animate-pulse"
              />
            ))}
          </div>
        ) : sortedEvents.length > 0 ? (
          sortedEvents.map((evt) => (
            <EventCard
              key={evt.event_id}
              event={evt}
              isSelected={selectedEvent?.event_id === evt.event_id}
              onSelect={handleSelect}
            />
          ))
        ) : (
          <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-border/80 rounded-control bg-surface/30">
            <FilterX className="w-6 h-6 text-foreground-muted mb-2" />
            <div className="text-xs text-foreground font-semibold">No Matching Anomalies</div>
            <div className="text-[10px] text-foreground-muted mt-1 max-w-[200px]">
              No thermal events match active search or time-window criteria.
            </div>
            <button
              onClick={resetFilters}
              className="mt-3 px-2.5 py-1 text-[10px] rounded-control bg-accent/15 border border-accent/30 text-accent hover:bg-accent/25 transition-colors"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* 5. Provenance & Calibration Footer */}
      <div className="mt-2.5 pt-2 border-t border-border/60 text-[9px] text-foreground-muted flex items-center justify-between">
        <span className="flex items-center gap-1">
          <Cpu className="w-2.5 h-2.5 text-accent-cyan" /> {APP_CONFIG.modelName}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-2.5 h-2.5 text-foreground-muted" /> {APP_CONFIG.featureSchema}
        </span>
      </div>
    </Panel>
  );
}
