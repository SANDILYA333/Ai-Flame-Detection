"use client";

import dynamic from "next/dynamic";

const AppShell = dynamic(
  () => import("@/components/app-shell/AppShell").then((mod) => mod.AppShell),
  {
    ssr: false,
    loading: () => (
      <div className="h-screen w-screen bg-[#07090d] flex items-center justify-center text-[#f2f5f7] font-mono text-xs select-none">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#39ff88]/20 border-t-[#39ff88] animate-spin" />
          <span className="tracking-widest uppercase text-[#737e89]">
            INITIALIZING FLAME INTELLIGENCE MISSION CONTROL...
          </span>
        </div>
      </div>
    ),
  }
);

export default function Home() {
  return <AppShell />;
}
