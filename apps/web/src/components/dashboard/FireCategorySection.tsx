"use client";

import React from "react";
import {
  Trees,
  Factory,
  Flame,
  Clock,
  Tractor,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { useEventContext } from "@/context/EventContext";
import {
  FIRE_CATEGORIES,
  FireCategoryType,
} from "@/lib/categories/fireCategories";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
  Trees,
  Factory,
  Flame,
  Clock,
  Tractor,
  HelpCircle,
};

export interface FireCategorySectionProps {
  onSelectCategory?: (category: FireCategoryType) => void;
}

export function FireCategorySection({ onSelectCategory }: FireCategorySectionProps) {
  const { categoryMetrics, selectedCategory, setSelectedCategory } = useEventContext();

  const handleCategoryClick = (categoryId: FireCategoryType) => {
    if (selectedCategory === categoryId) {
      setSelectedCategory("ALL");
      if (onSelectCategory) onSelectCategory("ALL");
    } else {
      setSelectedCategory(categoryId);
      if (onSelectCategory) onSelectCategory(categoryId);
    }
  };

  return (
    <div className="flex flex-col gap-3 font-mono">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-foreground tracking-wider uppercase">
            FIRE & THERMAL CATEGORIES
          </span>
          <span className="text-[10px] text-foreground-muted">
            (Select to explore incidents)
          </span>
        </div>
        {selectedCategory !== "ALL" && (
          <button
            onClick={() => handleCategoryClick("ALL")}
            className="text-[11px] text-accent hover:underline flex items-center gap-1"
          >
            <span>Show All Categories</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {FIRE_CATEGORIES.map((cat) => {
          const Icon = ICON_MAP[cat.iconName] || Flame;
          const metrics = categoryMetrics[cat.id];
          const isSelected = selectedCategory === cat.id;

          return (
            <div
              key={cat.id}
              onClick={() => handleCategoryClick(cat.id)}
              className={cn(
                "group relative bg-surface border rounded-panel p-4 shadow-panel cursor-pointer transition-all duration-200 flex flex-col justify-between select-none",
                isSelected
                  ? "border-accent bg-surface-raised ring-1 ring-accent"
                  : "border-border hover:border-border-strong hover:bg-surface-hover/80"
              )}
            >
              <div>
                {/* Header: Icon, Category Name, Active Status */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={cn(
                        "w-8 h-8 rounded-control flex items-center justify-center transition-transform group-hover:scale-105",
                        cat.badgeBg,
                        cat.badgeBorder,
                        "border"
                      )}
                      style={{ color: cat.accentColor }}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-foreground group-hover:text-accent transition-colors leading-snug">
                        {cat.title}
                      </h4>
                      <span className="text-[10px] text-foreground-muted">
                        {cat.shortLabel}
                      </span>
                    </div>
                  </div>

                  {/* Total Event Count Pill */}
                  <div
                    className={cn(
                      "px-2 py-0.5 rounded-pill text-xs font-bold border",
                      cat.badgeBg,
                      cat.badgeBorder,
                      cat.badgeText
                    )}
                  >
                    {metrics?.totalCount || 0}
                  </div>
                </div>

                {/* Description */}
                <p className="text-[11px] text-foreground-secondary leading-relaxed mb-3 line-clamp-2">
                  {cat.description}
                </p>
              </div>

              {/* Footer: Severity breakdown & Explore CTA */}
              <div className="pt-2 border-t border-border flex items-center justify-between text-[10px]">
                <div className="flex items-center gap-2 text-foreground-muted">
                  {metrics && metrics.criticalCount > 0 && (
                    <span className="flex items-center gap-1 text-state-error font-semibold">
                      <ShieldAlert className="w-3 h-3" />
                      {metrics.criticalCount} Critical
                    </span>
                  )}
                  {metrics && metrics.highCount > 0 && (
                    <span className="text-state-warning font-semibold">
                      {metrics.highCount} High
                    </span>
                  )}
                  {metrics && metrics.maxFrp > 0 && (
                    <span className="text-foreground-secondary">
                      Max: {metrics.maxFrp.toFixed(0)} MW
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1 text-accent font-semibold group-hover:translate-x-0.5 transition-transform">
                  <span>Explore</span>
                  <ArrowRight className="w-3 h-3" />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
