"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bell,
  Settings,
  Flame,
  Sliders,
  ShieldAlert,
  ChevronLeft,
  LayoutDashboard,
  Compass,
  MapPin,
} from "lucide-react";
import { StatusDot } from "@/components/ui/StatusDot";
import { SearchInput } from "@/components/ui/SearchInput";
import { IconButton } from "@/components/ui/IconButton";
import { Tooltip } from "@/components/ui/Tooltip";
import { Badge } from "@/components/ui/Badge";
import { APP_CONFIG } from "@/config/ui";
import { formatUtcDateTime } from "@/lib/format/dates";
import { useEventContext } from "@/context/EventContext";
import { AiSimulationLabModal } from "@/components/simulation/AiSimulationLabModal";
import { AgniAssistant } from "@/components/agni";
import { cn } from "@/lib/utils";

const CLASSIFICATION_FILTERS = [
  { id: "ALL", label: "ALL" },
  { id: "INDUSTRIAL", label: "INDUSTRIAL" },
  { id: "NON_INDUSTRIAL", label: "NON-IND" },
  { id: "UNKNOWN", label: "UNKNOWN" },
  { id: "REVIEW_REQUIRED", label: "REVIEW" },
];

export function TopBar() {
  const [currentTime, setCurrentTime] = useState<string>("");
  const [isSimLabOpen, setIsSimLabOpen] = useState(false);

  const {
    activeViewMode,
    setActiveViewMode,
    selectedCountry,
    selectedState,
    selectedDistrict,
    returnToDashboard,
    searchQuery,
    setSearchQuery,
    selectedClassification,
    setSelectedClassification,
    filteredEvents,
    rawEvents,
    isLiveBackend,
  } = useEventContext();

  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const updateTime = () => setCurrentTime(formatUtcDateTime(new Date()));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Global ⌘K / Ctrl+K keyboard shortcut to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <header className="h-12 w-full bg-surface border-b border-border flex items-center justify-between px-3 z-40 select-none shrink-0 shadow-panel gap-2">
        {/* 1. Left: Brand Identity, Return Action & View Switcher */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-control bg-thermal/15 border border-thermal/40 flex items-center justify-center text-thermal glow-thermal">
              <Flame className="w-4 h-4 text-thermal-primary animate-flame" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-xs font-bold font-sans tracking-wider uppercase text-foreground">
                  {APP_CONFIG.name}
                </span>
                <Badge
                  variant="neutral"
                  size="sm"
                  className="hidden sm:inline-flex text-[9px] px-1 py-0"
                >
                  {APP_CONFIG.shortName}
                </Badge>
              </div>
              <div className="text-[9px] font-mono text-foreground-muted hidden md:block mt-0.5">
                {APP_CONFIG.tagline}
              </div>
            </div>
          </div>

          <div className="h-4 w-[1px] bg-border mx-1 hidden sm:block" />

          {/* Primary View Mode Switcher (Level 1 Dashboard vs Level 2 Advanced Mission Control) */}
          <div className="flex items-center bg-surface-raised p-0.5 rounded-control border border-border">
            <button
              onClick={() => setActiveViewMode("DASHBOARD")}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 text-[10px] font-mono font-bold rounded-sm transition-all",
                activeViewMode === "DASHBOARD"
                  ? "bg-accent text-background shadow-sm"
                  : "text-foreground-secondary hover:text-foreground"
              )}
            >
              <LayoutDashboard className="w-3 h-3" />
              <span>DASHBOARD</span>
            </button>
            <button
              onClick={() => setActiveViewMode("MISSION_CONTROL")}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 text-[10px] font-mono font-bold rounded-sm transition-all",
                activeViewMode === "MISSION_CONTROL"
                  ? "bg-accent text-background shadow-sm"
                  : "text-foreground-secondary hover:text-foreground"
              )}
            >
              <Compass className="w-3 h-3" />
              <span>ADVANCED ANALYSIS</span>
            </button>
          </div>

          {/* Return to Dashboard Quick Action when in Advanced Mission Control */}
          {activeViewMode === "MISSION_CONTROL" && (
            <button
              onClick={returnToDashboard}
              title="Return to Simple Fire Intelligence Dashboard"
              className="hidden lg:flex items-center gap-1 px-2 py-1 text-[10px] font-mono font-semibold rounded bg-surface-raised hover:bg-surface-hover border border-border text-accent transition-colors"
            >
              <ChevronLeft className="w-3 h-3" />
              <span>Back to Dashboard</span>
            </button>
          )}

          {/* Active Scope Indicator Badge */}
          {selectedState !== "ALL" && (
            <div className="hidden xl:flex items-center gap-1 px-2 py-0.5 rounded-control bg-accent-cyan/10 border border-accent-cyan/30 text-accent-cyan text-[10px] font-mono font-semibold">
              <MapPin className="w-3 h-3" />
              <span>
                {selectedState}
                {selectedDistrict !== "ALL" ? ` > ${selectedDistrict}` : ""}
              </span>
            </div>
          )}
        </div>

        {/* 2. Center: Search & Quick Classification Chips */}
        <div className="flex items-center gap-2 flex-1 max-w-lg mx-2">
          <div className="relative flex-1">
            <SearchInput
              ref={searchInputRef}
              placeholder="Search event ID, cluster, refinery, power station..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClear={() => setSearchQuery("")}
              shortcut="⌘K"
            />
          </div>

          {/* Quick classification filter pills (when in Mission Control) */}
          {activeViewMode === "MISSION_CONTROL" && (
            <div className="hidden xl:flex items-center gap-1 bg-surface-raised p-0.5 rounded-control border border-border">
              {CLASSIFICATION_FILTERS.map((filter) => {
                const isSelected = selectedClassification === filter.id;
                return (
                  <button
                    key={filter.id}
                    onClick={() => setSelectedClassification(filter.id)}
                    className={cn(
                      "px-2 py-0.5 text-[10px] font-mono rounded-sm transition-all duration-150",
                      isSelected
                        ? filter.id === "ALL"
                          ? "bg-accent text-background font-bold shadow-sm"
                          : filter.id === "INDUSTRIAL"
                          ? "bg-accent text-background font-bold shadow-sm"
                          : filter.id === "NON_INDUSTRIAL"
                          ? "bg-state-warning text-background font-bold shadow-sm"
                          : filter.id === "UNKNOWN"
                          ? "bg-accent-cyan text-background font-bold shadow-sm"
                          : filter.id === "REVIEW_REQUIRED"
                          ? "bg-state-error text-white font-bold shadow-sm"
                          : "bg-accent text-background font-bold shadow-sm"
                        : "text-foreground-muted hover:text-foreground hover:bg-surface-hover/60"
                    )}
                  >
                    {filter.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 3. Right: AGNI Voice Assistant, AI Simulation Lab Trigger, Live Clock & Telemetry */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* AGNI AI Voice Intelligence Assistant */}
          <AgniAssistant onOpenSimLab={() => setIsSimLabOpen(true)} />

          {/* AI Simulation Lab Button */}
          <button
            onClick={() => setIsSimLabOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono font-bold rounded bg-accent/15 hover:bg-accent/25 border border-accent/40 text-accent transition-colors shadow-sm"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">AI SIM LAB</span>
          </button>

          {/* Filter matches badge */}
          <div className="hidden md:flex items-center gap-1 text-[11px] font-mono text-foreground-secondary bg-surface-raised px-2 py-0.5 rounded-control border border-border">
            <span className="text-foreground font-semibold">{filteredEvents.length}</span>
            <span className="text-foreground-muted">/ {rawEvents.length} Evts</span>
          </div>

          {/* Live UTC Clock */}
          <div className="hidden lg:flex flex-col items-end text-right font-mono">
            <span className="text-[11px] font-semibold text-foreground tracking-wider">
              {currentTime || "UTC LIVE"}
            </span>
            <span className="text-[9px] text-foreground-muted">SYNCHRONIZED WGS84</span>
          </div>

          <div className="h-4 w-[1px] bg-border mx-1 hidden lg:block" />

          {/* System Settings & Notifications */}
          <div className="flex items-center gap-1">
            <Tooltip content="Active Operational Alerts" position="bottom">
              <IconButton ariaLabel="Notifications" size="sm">
                <Bell className="w-3.5 h-3.5" />
              </IconButton>
            </Tooltip>

            <Tooltip content="Platform Configuration" position="bottom">
              <IconButton ariaLabel="Settings" size="sm">
                <Settings className="w-3.5 h-3.5" />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </header>

      {/* AI Simulation Lab Modal */}
      <AiSimulationLabModal
        isOpen={isSimLabOpen}
        onClose={() => setIsSimLabOpen(false)}
      />
    </>
  );
}
