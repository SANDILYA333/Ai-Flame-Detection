"use client";

import React from "react";
import { MapWorkspace } from "./MapWorkspace";
import { cn } from "@/lib/utils";

export interface MapCanvasProps {
  className?: string;
}

export function MapCanvas({ className }: MapCanvasProps) {
  return (
    <main className={cn("relative flex-1 w-full h-full overflow-hidden bg-base", className)}>
      <MapWorkspace />
    </main>
  );
}
