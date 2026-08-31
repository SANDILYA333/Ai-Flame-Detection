"use client";

import React from "react";
import { AlertTriangle, Map } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface WebGLFallbackProps {
  onSwitchTo2D?: () => void;
  className?: string;
}

export function WebGLFallback({ onSwitchTo2D, className }: WebGLFallbackProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center bg-surface/90 backdrop-blur-md border border-border rounded-panel max-w-md mx-auto shadow-panel",
        className
      )}
    >
      <div className="w-10 h-10 rounded-full bg-state-warning/15 border border-state-warning/30 flex items-center justify-center text-state-warning mb-3">
        <AlertTriangle className="w-5 h-5" />
      </div>

      <h3 className="text-sm font-semibold tracking-wider uppercase text-foreground font-sans">
        3D Acceleration Unavailable
      </h3>

      <p className="text-xs text-foreground-muted font-mono mt-1.5 leading-relaxed">
        Your browser or display adapter does not support WebGL 3D graphics rendering.
        Switch to the optimized 2D GIS projection to continue operational monitoring.
      </p>

      {onSwitchTo2D && (
        <Button
          variant="primary"
          size="md"
          onClick={onSwitchTo2D}
          leftIcon={<Map className="w-3.5 h-3.5" />}
          className="mt-4"
        >
          Activate 2D Map Engine
        </Button>
      )}
    </div>
  );
}
