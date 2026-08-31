"use client";

import React from "react";
import { TopBar } from "./TopBar";
import { StatusBar } from "./StatusBar";
import { Workspace } from "./Workspace";
import { EventProvider } from "@/context/EventContext";

export function AppShell() {
  return (
    <EventProvider>
      <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground select-none">
        {/* 1. Top Command Bar */}
        <TopBar />

        {/* 2. Main Spatial Workspace */}
        <Workspace />

        {/* 3. Operational Bottom Telemetry Bar */}
        <StatusBar />
      </div>
    </EventProvider>
  );
}
