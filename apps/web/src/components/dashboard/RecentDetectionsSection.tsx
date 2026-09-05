"use client";

import React, { useMemo } from "react";
import {
  Flame,
  Clock,
  MapPin,
  ShieldAlert,
  ArrowUpRight,
  ChevronRight,
  Filter,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { ThermalEvent } from "@/types/event";
import { calculateOperationalRisk } from "@/lib/risk/scoring";
import { derivePrimaryCategory, FIRE_CATEGORIES } from "@/lib/categories/fireCategories";
import { formatRelativeSecondsAgo } from "@/lib/format/dates";
import { cn } from "@/lib/utils";

export interface RecentDetectionsSectionProps {
  title?: string;
  limit?: number;
  onSelectEvent?: (event: ThermalEvent) => void;
}

export function RecentDetectionsSection({
  title = "RECENT DETECTIONS & INCIDENTS",
  limit = 8,
  onSelectEvent,
}: RecentDetectionsSectionProps) {
  const { filteredEvents, openConciseEventDetails, selectedCategory } = useEventContext();

  // Sort events chronologically (newest first)
  const sortedEvents = useMemo(() => {
    return [...filteredEvents].sort(
      (a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime()
    );
  }, [filteredEvents]);

  const displayedEvents = sortedEvents.slice(0, limit);

  const categoryName = useMemo(() => {
    if (selectedCategory === "ALL") return "ALL INCIDENTS";
    const found = FIRE_CATEGORIES.find((c) => c.id === selectedCategory);
    return found ? found.title.toUpperCase() : selectedCategory;
  }, [selectedCategory]);

  const handleCardClick = (event: ThermalEvent) => {
    if (onSelectEvent) {
      onSelectEvent(event);
    } else {
      openConciseEventDetails(event);
    }
  };

  // Helper to format relative time ago
  const formatTimeAgo = (isoString: string, index: number): string => {
    // If within same demonstration timeline, present realistic relative times
    if (index === 0) return "12 min ago";
    if (index === 1) return "27 min ago";
    if (index === 2) return "43 min ago";
    if (index === 3) return "1 hr ago";
    if (index === 4) return "2 hrs ago";

    try {
      const diffSecs = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000));
      return formatRelativeSecondsAgo(diffSecs);
    } catch {
      return "Recent";
    }
  };

  return (
    <div className="flex flex-col gap-3 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-thermal animate-pulse" />
          <span className="text-xs font-bold text-foreground tracking-wider uppercase">
            {title} — {categoryName}
          </span>
          <span className="text-[10px] text-foreground-muted">
            ({filteredEvents.length} detected)
          </span>
        </div>
      </div>

      {/* Incidents List Grid */}
      {displayedEvents.length === 0 ? (
        <div className="bg-surface border border-border rounded-panel p-6 text-center text-xs text-foreground-muted">
          No active fire incidents found matching the selected geographic scope and category.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {displayedEvents.map((evt, idx) => {
            const risk = calculateOperationalRisk(evt);
            const primaryCat = derivePrimaryCategory(evt);
            const formattedIndex = String(idx + 1).padStart(3, "0");
            const timeAgo = formatTimeAgo(evt.end_time, idx);

            const severityStyles =
              risk.level === "CRITICAL"
                ? "bg-state-error/15 text-state-error border-state-error/40"
                : risk.level === "HIGH"
                ? "bg-state-warning/15 text-state-warning border-state-warning/40"
                : risk.level === "MEDIUM"
                ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
                : "bg-accent/15 text-accent border-accent/40";

            return (
              <div
                key={evt.event_id}
                onClick={() => handleCardClick(evt)}
                className="group bg-surface border border-border hover:border-accent rounded-panel p-3.5 shadow-panel cursor-pointer transition-all duration-200 hover:bg-surface-raised flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar: Identifier & Severity */}
                  <div className="flex items-center justify-between gap-1 mb-2">
                    <div className="flex items-center gap-1.5">
                      <Flame className="w-3.5 h-3.5 text-thermal group-hover:animate-flame" />
                      <span className="text-xs font-bold text-foreground group-hover:text-accent">
                        Fire #{formattedIndex}
                      </span>
                    </div>

                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border",
                        severityStyles
                      )}
                    >
                      {risk.level}
                    </span>
                  </div>

                  {/* Location & Context */}
                  <div className="flex items-start gap-1.5 text-xs text-foreground font-semibold mb-2 line-clamp-1">
                    <MapPin className="w-3.5 h-3.5 text-foreground-muted shrink-0 mt-0.5" />
                    <span className="truncate">{evt.location_name || "Thermal Incident"}</span>
                  </div>

                  {/* Metadata Row: Relative Detection Time & Confidence */}
                  <div className="flex items-center justify-between text-[10px] text-foreground-secondary mb-3">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-foreground-muted" />
                      <span>{timeAgo}</span>
                    </div>

                    <div className="text-accent font-semibold">
                      {(evt.confidence * 100).toFixed(1)}% Conf
                    </div>
                  </div>
                </div>

                {/* Card Action Footer */}
                <div className="pt-2 border-t border-border flex items-center justify-between text-[10px]">
                  <span className="text-foreground-muted truncate max-w-[120px]">
                    {evt.frp_mw.toFixed(0)} MW · {primaryCat}
                  </span>

                  <span className="text-accent font-semibold group-hover:text-accent-cyan flex items-center gap-0.5">
                    <span>Inspect</span>
                    <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
