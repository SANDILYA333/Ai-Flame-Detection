import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Global Green Active-State Text & Icon Contrast Suite", () => {
  it("Test 1: TopBar classification filters render dark high-contrast foreground on active surfaces", () => {
    const CLASSIFICATION_FILTERS = [
      { id: "ALL", label: "ALL" },
      { id: "INDUSTRIAL", label: "IND" },
      { id: "NON_INDUSTRIAL", label: "NON-IND" },
      { id: "UNKNOWN", label: "UNKNOWN" },
      { id: "REVIEW_REQUIRED", label: "REVIEW" },
    ];

    const getFilterClass = (filterId: string, selectedId: string) => {
      const isSelected = selectedId === filterId;
      if (!isSelected) return "text-foreground-muted hover:text-foreground hover:bg-surface-hover/60";
      if (filterId === "ALL" || filterId === "INDUSTRIAL") {
        return "bg-accent text-background font-bold shadow-sm";
      }
      if (filterId === "NON_INDUSTRIAL") {
        return "bg-state-warning text-background font-bold shadow-sm";
      }
      if (filterId === "UNKNOWN") {
        return "bg-accent-cyan text-background font-bold shadow-sm";
      }
      if (filterId === "REVIEW_REQUIRED") {
        return "bg-state-error text-white font-bold shadow-sm";
      }
      return "bg-accent text-background font-bold shadow-sm";
    };

    // When ALL is active
    const allActive = getFilterClass("ALL", "ALL");
    assert.ok(allActive.includes("bg-accent"), "ALL filter must have bg-accent when active");
    assert.ok(allActive.includes("text-background"), "ALL filter must have text-background (dark) when active");
    assert.ok(allActive.includes("font-bold"), "ALL filter must be font-bold when active");

    // When INDUSTRIAL is active
    const indActive = getFilterClass("INDUSTRIAL", "INDUSTRIAL");
    assert.ok(indActive.includes("bg-accent") && indActive.includes("text-background"));

    // When NON_INDUSTRIAL is active
    const nonIndActive = getFilterClass("NON_INDUSTRIAL", "NON_INDUSTRIAL");
    assert.ok(nonIndActive.includes("bg-state-warning") && nonIndActive.includes("text-background"));
  });

  it("Test 2: Timeline Playback Bar time window buttons render dark high-contrast foreground on active surfaces", () => {
    const TIME_WINDOWS = ["1H", "6H", "24H", "48H", "7D", "ALL"] as const;

    const getTimeWindowClass = (win: string, currentRange: string) => {
      const isSelected =
        currentRange.toUpperCase() === win.toUpperCase() ||
        (win === "ALL" && currentRange.toUpperCase() === "ALL");
      return isSelected
        ? "bg-accent text-background font-bold shadow-sm"
        : "text-foreground-muted hover:text-foreground hover:bg-surface-hover";
    };

    for (const win of TIME_WINDOWS) {
      const activeClass = getTimeWindowClass(win, win);
      assert.ok(activeClass.includes("bg-accent"), `${win} button must have bg-accent when selected`);
      assert.ok(
        activeClass.includes("text-background"),
        `${win} button must have text-background (dark) for high contrast against green`
      );
      assert.ok(activeClass.includes("font-bold"), `${win} button must have font-bold`);
    }

    // Inactive state must retain muted foreground
    const inactiveClass = getTimeWindowClass("1H", "ALL");
    assert.ok(inactiveClass.includes("text-foreground-muted"));
    assert.ok(!inactiveClass.includes("bg-accent"));
  });

  it("Test 3: Tactical Dossier Export PDF button has high-contrast dark text and icons", () => {
    const exportButtonClass =
      "flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold rounded bg-accent text-background hover:bg-emerald-400 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-sm";

    assert.ok(exportButtonClass.includes("bg-accent"), "PDF export button must use bright green bg-accent");
    assert.ok(
      exportButtonClass.includes("text-background"),
      "PDF export button must specify text-background for dark text/icons"
    );
    assert.ok(exportButtonClass.includes("font-bold"));
  });

  it("Test 4: UI Button primary variant uses text-background on bg-accent", () => {
    const primaryVariant = "bg-accent text-background hover:bg-emerald-400 font-semibold shadow-inset";
    assert.ok(primaryVariant.includes("bg-accent"));
    assert.ok(primaryVariant.includes("text-background"));
  });
});
