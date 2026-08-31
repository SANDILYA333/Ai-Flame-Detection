"use client";

import React from "react";
import { Globe, Map } from "lucide-react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";

export type ViewMode = "2D" | "3D";

export interface ViewModeToggleProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
  className?: string;
}

export function ViewModeToggle({ mode, onChange, className }: ViewModeToggleProps) {
  return (
    <SegmentedControl<ViewMode>
      value={mode}
      onChange={onChange}
      size="sm"
      className={className}
      options={[
        {
          value: "2D",
          label: "2D Map",
          icon: <Map className="w-3 h-3" />,
        },
        {
          value: "3D",
          label: "3D Globe",
          icon: <Globe className="w-3 h-3" />,
        },
      ]}
    />
  );
}
