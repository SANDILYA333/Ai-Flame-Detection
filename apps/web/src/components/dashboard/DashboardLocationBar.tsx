"use client";

import React, { useMemo } from "react";
import { MapPin, Globe, RotateCcw, Filter, ChevronRight } from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import { extractAvailableLocations } from "@/lib/location/locationFilter";

export function DashboardLocationBar() {
  const {
    rawEvents,
    selectedCountry,
    selectedState,
    selectedDistrict,
    setSelectedLocation,
    resetLocationFilter,
    filteredEvents,
  } = useEventContext();

  const { countries, states, districts } = useMemo(() => {
    return extractAvailableLocations(rawEvents);
  }, [rawEvents]);

  // Filter districts available for the selected state
  const availableDistricts = useMemo(() => {
    if (selectedState === "ALL") return districts;
    return districts.filter(
      (d) => d.state.toLowerCase() === selectedState.toLowerCase()
    );
  }, [districts, selectedState]);

  const hasActiveFilter =
    selectedCountry !== "ALL" ||
    selectedState !== "ALL" ||
    selectedDistrict !== "ALL";

  return (
    <div className="bg-surface border border-border rounded-panel p-3 shadow-panel flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 font-mono">
      {/* 1. Left: Scope Summary & Breadcrumb */}
      <div className="flex items-center gap-2 text-xs">
        <div className="w-7 h-7 rounded-control bg-accent-cyan/15 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan shrink-0">
          <MapPin className="w-3.5 h-3.5 animate-pulse-subtle" />
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-foreground-muted uppercase tracking-wider">
            GEOGRAPHIC SCOPE
          </span>
          <div className="flex items-center gap-1.5 text-foreground font-semibold">
            <span className="text-accent-cyan">{selectedCountry || "Global"}</span>
            <ChevronRight className="w-3 h-3 text-border-strong" />
            <span className={selectedState !== "ALL" ? "text-accent" : "text-foreground-secondary"}>
              {selectedState !== "ALL" ? selectedState : "All States"}
            </span>
            {selectedDistrict !== "ALL" && (
              <>
                <ChevronRight className="w-3 h-3 text-border-strong" />
                <span className="text-thermal font-bold">{selectedDistrict}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 2. Center: Location Filter Dropdowns */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Country Selector */}
        <div className="flex items-center gap-1 bg-surface-raised border border-border px-2 py-1 rounded-control">
          <Globe className="w-3.5 h-3.5 text-foreground-muted shrink-0" />
          <select
            aria-label="Country Filter"
            value={selectedCountry}
            onChange={(e) => setSelectedLocation(e.target.value, "ALL", "ALL")}
            className="bg-transparent text-xs text-foreground focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-surface text-foreground">
              All Countries
            </option>
            {countries.map((c) => (
              <option key={c.id} value={c.name} className="bg-surface text-foreground">
                {c.name} ({c.count})
              </option>
            ))}
          </select>
        </div>

        {/* State Selector */}
        <div className="flex items-center gap-1 bg-surface-raised border border-border px-2 py-1 rounded-control">
          <span className="text-[10px] text-foreground-muted uppercase">State:</span>
          <select
            aria-label="State Filter"
            value={selectedState}
            onChange={(e) => setSelectedLocation(undefined, e.target.value, "ALL")}
            className="bg-transparent text-xs text-foreground font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-surface text-foreground">
              All States ({rawEvents.length})
            </option>
            {states.map((s) => (
              <option key={s.id} value={s.name} className="bg-surface text-foreground">
                {s.name} ({s.count})
              </option>
            ))}
          </select>
        </div>

        {/* District Selector */}
        <div className="flex items-center gap-1 bg-surface-raised border border-border px-2 py-1 rounded-control">
          <span className="text-[10px] text-foreground-muted uppercase">District:</span>
          <select
            aria-label="District Filter"
            value={selectedDistrict}
            onChange={(e) => setSelectedLocation(undefined, undefined, e.target.value)}
            className="bg-transparent text-xs text-foreground font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-surface text-foreground">
              All Districts
            </option>
            {availableDistricts.map((d) => (
              <option key={d.id} value={d.name} className="bg-surface text-foreground">
                {d.name} ({d.count})
              </option>
            ))}
          </select>
        </div>

        {/* Reset Filter Button */}
        {hasActiveFilter && (
          <button
            onClick={resetLocationFilter}
            title="Reset Location Scope"
            className="flex items-center gap-1 px-2.5 py-1 text-xs bg-surface-hover hover:bg-surface-raised border border-border text-foreground-muted hover:text-foreground rounded-control transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* 3. Right: Matching Events Live Counter */}
      <div className="flex items-center gap-2 self-end md:self-auto shrink-0 text-xs">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-pill bg-accent/10 border border-accent/30 text-accent font-semibold">
          <Filter className="w-3 h-3" />
          <span>{filteredEvents.length} Incidents in Scope</span>
        </div>
      </div>
    </div>
  );
}
