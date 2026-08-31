"use client";

import React from "react";
import { MapCanvas } from "@/components/map/MapCanvas";

export function Workspace() {
  return (
    <div className="relative flex-1 w-full h-full overflow-hidden flex flex-col">
      <MapCanvas />
    </div>
  );
}
