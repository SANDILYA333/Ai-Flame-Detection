"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface EventDetailSkeletonProps {
  className?: string;
}

export function EventDetailSkeleton({ className }: EventDetailSkeletonProps) {
  return (
    <div
      className={cn(
        "w-full sm:w-96 p-4 rounded-panel bg-surface-raised/95 backdrop-blur-md border border-border space-y-3 font-mono text-xs select-none",
        className
      )}
    >
      {/* Header skeleton */}
      <div className="flex items-center justify-between border-b border-border pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-control bg-surface-hover animate-pulse" />
          <div className="space-y-1">
            <div className="w-24 h-3.5 bg-surface-hover rounded animate-pulse" />
            <div className="w-32 h-2.5 bg-surface-hover/60 rounded animate-pulse" />
          </div>
        </div>
        <div className="w-12 h-6 bg-surface-hover rounded animate-pulse" />
      </div>

      {/* Classification & Confidence skeleton */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-20 h-5 bg-surface-hover rounded-control animate-pulse" />
          <div className="w-16 h-5 bg-surface-hover rounded-control animate-pulse" />
          <div className="w-24 h-5 bg-surface-hover rounded-control animate-pulse" />
        </div>
        <div className="w-full h-8 bg-surface-hover/70 rounded-control animate-pulse" />
      </div>

      {/* Metrics grid skeleton */}
      <div className="grid grid-cols-2 gap-2">
        <div className="h-14 bg-surface-hover/50 rounded-control animate-pulse" />
        <div className="h-14 bg-surface-hover/50 rounded-control animate-pulse" />
      </div>

      {/* Evidence section skeleton */}
      <div className="h-28 bg-surface-hover/40 rounded-control animate-pulse" />

      {/* Footer skeleton */}
      <div className="h-6 bg-surface-hover/30 rounded-control animate-pulse" />
    </div>
  );
}
