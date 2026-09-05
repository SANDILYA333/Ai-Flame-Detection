"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { ThermalEvent } from "@/types/event";
import { useEventMedia } from "@/hooks/useEventMedia";
import {
  Newspaper,
  Video,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  Clock,
  Radio,
  Play,
  Info,
} from "lucide-react";

interface ContextualMediaSectionProps {
  event: ThermalEvent;
  className?: string;
}

export function ContextualMediaSection({
  event,
  className,
}: ContextualMediaSectionProps) {
  const [activeTab, setActiveTab] = useState<"NEWS" | "VIDEOS">("NEWS");
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);

  const { media, isLoading, isError } = useEventMedia(event.event_id);

  const newsItems = media?.news || [];
  const videoItems = media?.videos || [];

  return (
    <div
      data-testid="contextual-media-section"
      className={cn(
        "p-3 rounded-control bg-surface/90 border border-border/80 font-mono space-y-3",
        className
      )}
    >
      {/* 1. Header with Scientific vs External Context Labeling */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Radio className="w-3.5 h-3.5 text-accent animate-pulse-subtle shrink-0" />
          <span className="text-[11px] font-bold text-foreground uppercase tracking-wider truncate">
            CONTEXTUAL INTELLIGENCE & MEDIA
          </span>
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-raised border border-border text-foreground-muted uppercase">
          SECONDARY CONTEXT
        </span>
      </div>

      {/* 2. Media Sub-Tab Switcher */}
      <div className="flex items-center gap-1 bg-surface-raised p-0.5 rounded-control border border-border/60">
        <button
          type="button"
          onClick={() => {
            setActiveTab("NEWS");
            setActiveVideoId(null);
          }}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 py-1 px-2 text-[10px] font-bold rounded-sm transition-all",
            activeTab === "NEWS"
              ? "bg-accent/15 text-accent border border-accent/30 shadow-sm"
              : "text-foreground-secondary hover:text-foreground"
          )}
        >
          <Newspaper className="w-3 h-3" />
          <span>NEWS & COVERAGE ({newsItems.length})</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("VIDEOS")}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 py-1 px-2 text-[10px] font-bold rounded-sm transition-all",
            activeTab === "VIDEOS"
              ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 shadow-sm"
              : "text-foreground-secondary hover:text-foreground"
          )}
        >
          <Video className="w-3 h-3" />
          <span>BRIEFING VIDEOS ({videoItems.length})</span>
        </button>
      </div>

      {/* 3. Loading State */}
      {isLoading && (
        <div className="py-6 flex flex-col items-center justify-center gap-2 text-foreground-muted text-[10px]">
          <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <span>INDEXING EXTERNAL INTELLIGENCE...</span>
        </div>
      )}

      {/* 4. Tab 1: News & External Coverage */}
      {!isLoading && activeTab === "NEWS" && (
        <div className="space-y-2">
          {newsItems.length > 0 ? (
            newsItems.map((item) => (
              <div
                key={item.id}
                className="p-2.5 rounded-control bg-background/80 border border-border/60 space-y-1.5 hover:border-accent/40 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={cn(
                      "text-[8.5px] px-1.5 py-0.2 rounded font-bold uppercase shrink-0 border",
                      item.corroboration_type === "OFFICIAL_DISPATCH"
                        ? "bg-state-success/15 text-state-success border-state-success/30"
                        : "bg-surface-raised text-foreground-secondary border-border"
                    )}
                  >
                    {item.corroboration_type.replace(/_/g, " ")}
                  </span>
                  <div className="flex items-center gap-1 text-[9px] text-foreground-muted shrink-0">
                    <Clock className="w-2.5 h-2.5" />
                    <span>
                      {new Date(item.published_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] font-bold text-foreground hover:text-accent flex items-start gap-1 leading-snug group"
                >
                  <span className="line-clamp-2">{item.title}</span>
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5 text-accent" />
                </a>

                <p className="text-[10px] text-foreground-secondary leading-relaxed line-clamp-2">
                  {item.snippet}
                </p>

                <div className="pt-1 border-t border-border/30 flex items-center justify-between text-[9px] text-foreground-muted">
                  <span className="truncate max-w-[180px]">{item.source}</span>
                  <span className="text-accent font-bold">
                    Relevance {(item.relevance_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="py-4 px-3 rounded-control bg-background/50 border border-border/40 text-center space-y-1">
              <AlertCircle className="w-4 h-4 text-foreground-muted mx-auto" />
              <div className="text-[10.5px] font-bold text-foreground">
                No relevant external coverage found.
              </div>
              <p className="text-[9.5px] text-foreground-muted max-w-[260px] mx-auto">
                No corroborated news reports currently indexed for this spatial cluster.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 5. Tab 2: Videos & Briefings */}
      {!isLoading && activeTab === "VIDEOS" && (
        <div className="space-y-2">
          {activeVideoId ? (
            <div className="space-y-2">
              <div className="relative w-full aspect-video rounded-control overflow-hidden border border-border/80 bg-black">
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${activeVideoId}?autoplay=1&rel=0`}
                  title="Contextual Incident Video Briefing"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="w-full h-full border-0"
                />
              </div>
              <button
                type="button"
                onClick={() => setActiveVideoId(null)}
                className="w-full py-1 text-[9.5px] text-foreground-muted hover:text-foreground bg-surface-raised rounded-control border border-border transition-colors"
              >
                Close Video Player
              </button>
            </div>
          ) : videoItems.length > 0 ? (
            videoItems.map((v) => (
              <div
                key={v.id}
                onClick={() => setActiveVideoId(v.youtube_id)}
                className="group cursor-pointer p-2 rounded-control bg-background/80 border border-border/60 hover:border-accent-cyan/50 transition-all flex gap-2.5 items-center"
              >
                <div className="relative w-24 h-14 rounded overflow-hidden shrink-0 bg-black border border-border/40">
                  <img
                    src={v.thumbnail_url}
                    alt={v.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center group-hover:bg-black/20 transition-colors">
                    <Play className="w-4 h-4 text-white drop-shadow fill-white" />
                  </div>
                </div>

                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="text-[10.5px] font-bold text-foreground group-hover:text-accent-cyan transition-colors line-clamp-2 leading-tight">
                    {v.title}
                  </div>
                  <div className="text-[9px] text-foreground-muted truncate">
                    {v.channel_title}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-4 px-3 rounded-control bg-background/50 border border-border/40 text-center space-y-1">
              <AlertCircle className="w-4 h-4 text-foreground-muted mx-auto" />
              <div className="text-[10.5px] font-bold text-foreground">
                No relevant video briefings found.
              </div>
              <p className="text-[9.5px] text-foreground-muted max-w-[260px] mx-auto">
                No tactical YouTube footage or aerial reconnaissance linked to this event.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 6. Scientific Intelligence Disclaimer Stamp */}
      <div className="pt-1.5 border-t border-border/40 flex items-center gap-1.5 text-[8.5px] text-foreground-muted">
        <Info className="w-3 h-3 text-accent shrink-0" />
        <span className="leading-tight">
          External coverage is supplementary. Canonical NASA FIRMS telemetry remains primary.
        </span>
      </div>
    </div>
  );
}
