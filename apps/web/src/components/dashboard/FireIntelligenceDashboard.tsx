"use client";

import React from "react";
import { DashboardLocationBar } from "./DashboardLocationBar";
import { DashboardStatsGrid } from "./DashboardStatsGrid";
import { FireCategorySection } from "./FireCategorySection";
import { DashboardMapCard } from "./DashboardMapCard";
import { RecentDetectionsSection } from "./RecentDetectionsSection";
import { CategoryMonitoringView } from "./CategoryMonitoringView";
import { ConciseEventModal } from "./ConciseEventModal";
import { useEventContext } from "@/context/EventContext";

export function FireIntelligenceDashboard() {
  const { selectedCategory, setSelectedCategory } = useEventContext();

  return (
    <div className="relative flex-1 w-full h-full overflow-y-auto bg-background text-foreground p-3 sm:p-5 flex flex-col gap-4 max-w-7xl mx-auto font-mono select-none">
      {/* 1. Location Hierarchy & Geographic Scope Bar */}
      <DashboardLocationBar />

      {/* 2. Real-Time KPI Statistics Grid */}
      <DashboardStatsGrid />

      {/* 3. Main Operational Content */}
      {selectedCategory !== "ALL" ? (
        <CategoryMonitoringView
          category={selectedCategory}
          onBack={() => setSelectedCategory("ALL")}
        />
      ) : (
        <>
          {/* A. 6 Interactive Fire & Thermal Category Discovery Cards */}
          <FireCategorySection onSelectCategory={setSelectedCategory} />

          {/* B. Geospatial Overview Map Card */}
          <DashboardMapCard />

          {/* C. Recent Detections & Real Incident Stream */}
          <RecentDetectionsSection limit={8} />
        </>
      )}

      {/* 4. Concise Incident Details Modal */}
      <ConciseEventModal />
    </div>
  );
}
