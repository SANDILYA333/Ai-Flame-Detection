"use client";

import React from "react";
import { useEventContext } from "@/context/EventContext";
import { FireIntelligenceDashboard } from "@/components/dashboard/FireIntelligenceDashboard";
import { MapCanvas } from "@/components/map/MapCanvas";

export function Workspace() {
  const { activeViewMode } = useEventContext();

  return (
    <div className="relative flex-1 w-full h-full overflow-hidden flex flex-col bg-background">
      {activeViewMode === "DASHBOARD" ? (
        <FireIntelligenceDashboard />
      ) : (
        <MapCanvas />
      )}
    </div>
  );
}
