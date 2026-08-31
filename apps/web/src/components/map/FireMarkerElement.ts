import { ThermalEvent } from "@/types/event";
import { formatFrp } from "@/lib/format/numbers";
import { formatCoordinate } from "@/lib/format/coordinates";
import { formatUtcTime } from "@/lib/format/dates";

export interface CreateMarkerOptions {
  event: ThermalEvent;
  isSelected?: boolean;
  onSelect?: (event: ThermalEvent) => void;
}

export function createFireMarkerElement({
  event,
  isSelected = false,
  onSelect,
}: CreateMarkerOptions): HTMLElement {
  const el = document.createElement("div");
  el.className = "group relative flex items-center justify-center cursor-pointer select-none";
  el.style.transform = "translate(-50%, -50%) translateZ(0)";
  el.setAttribute("role", "button");
  el.setAttribute("tabindex", "0");
  el.setAttribute(
    "aria-label",
    `Thermal Event ${event.event_id}, ${event.classification}, ${event.frp_mw.toFixed(1)} MW`
  );

  // Size calculation based on FRP (MW)
  let markerSize = 28;
  let flameSize = 16;
  if (event.frp_mw > 250) {
    markerSize = 38;
    flameSize = 22;
  } else if (event.frp_mw > 100) {
    markerSize = 32;
    flameSize = 19;
  } else if (event.frp_mw > 40) {
    markerSize = 29;
    flameSize = 17;
  }

  // Classification styling
  const isIndustrial = event.classification === "INDUSTRIAL";
  const isUnknown = event.classification === "UNKNOWN";
  const isReviewRequired = event.uncertainty_state === "REVIEW_REQUIRED";

  const borderColor = isIndustrial
    ? "rgba(57, 255, 136, 0.85)"
    : isUnknown
    ? "rgba(0, 217, 255, 0.85)"
    : "rgba(255, 191, 36, 0.85)";

  const glowColor = isIndustrial
    ? "rgba(57, 255, 136, 0.5)"
    : isUnknown
    ? "rgba(0, 217, 255, 0.35)"
    : "rgba(255, 191, 36, 0.45)";

  // Outer Radiating Wave (for high intensity events)
  if (event.frp_mw > 80) {
    const wave = document.createElement("div");
    wave.className = "absolute rounded-full pointer-events-none animate-thermal-wave";
    wave.style.width = `${markerSize}px`;
    wave.style.height = `${markerSize}px`;
    wave.style.border = `1.5px solid ${glowColor}`;
    el.appendChild(wave);
  }

  // Core Marker Container
  const core = document.createElement("div");
  core.className = `relative flex items-center justify-center rounded-full transition-transform duration-150 group-hover:scale-115 active:scale-95 ${
    isSelected ? "animate-selection-pulse ring-2 ring-accent ring-offset-2 ring-offset-background" : ""
  }`;
  core.style.width = `${markerSize}px`;
  core.style.height = `${markerSize}px`;
  core.style.backgroundColor = "rgba(7, 9, 13, 0.92)";
  core.style.border = `2px solid ${isSelected ? "#39ff88" : borderColor}`;
  core.style.boxShadow = isSelected ? "0 0 14px rgba(57, 255, 136, 0.85)" : `0 0 8px ${glowColor}`;

  // Flame Emoji
  const flame = document.createElement("span");
  flame.className = "animate-flame";
  flame.style.fontSize = `${flameSize}px`;
  flame.style.lineHeight = "1";
  flame.innerText = "🔥";
  core.appendChild(flame);

  // Review Required Badge
  if (isReviewRequired) {
    const warningBadge = document.createElement("div");
    warningBadge.className =
      "absolute -top-1 -right-1 w-3.5 h-3.5 bg-state-warning text-bg-base text-[9px] font-mono font-bold rounded-full flex items-center justify-center border border-bg-base";
    warningBadge.innerText = "!";
    core.appendChild(warningBadge);
  }

  el.appendChild(core);

  // Hover Tooltip Popup with full metadata
  const coordText = formatCoordinate(event.latitude, event.longitude);
  const timeText = event.start_time ? formatUtcTime(event.start_time) : "LIVE";

  const tooltip = document.createElement("div");
  tooltip.className =
    "absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center pointer-events-none z-50 animate-in fade-in zoom-in-95 duration-150";
  tooltip.innerHTML = `
    <div class="bg-surface-raised/95 border border-border text-foreground px-2.5 py-1.5 rounded-control shadow-panel text-[11px] font-mono whitespace-nowrap backdrop-blur-md">
      <div class="flex items-center gap-1.5 font-bold">
        <span class="text-thermal-primary font-sans">🔥</span>
        <span>${event.event_id}</span>
        <span class="text-[9px] px-1 py-0.5 rounded uppercase font-semibold ${
          isIndustrial
            ? "bg-accent/15 text-accent border border-accent/30"
            : isUnknown
            ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
            : "bg-state-warning/15 text-state-warning border border-state-warning/30"
        }">${event.classification}</span>
      </div>
      <div class="text-[10px] text-foreground-muted mt-1 flex items-center justify-between gap-3 font-mono">
        <span class="text-foreground font-semibold">${formatFrp(event.frp_mw)}</span>
        <span>${(event.confidence * 100).toFixed(0)}% CONF</span>
      </div>
      <div class="text-[9px] text-foreground-muted/80 mt-0.5 flex items-center justify-between gap-2 border-t border-border/50 pt-0.5 font-mono">
        <span>${coordText}</span>
        <span>${timeText}</span>
      </div>
    </div>
    <div class="w-1.5 h-1.5 bg-surface-raised border-r border-b border-border rotate-45 -mt-1"></div>
  `;
  el.appendChild(tooltip);

  // Click / Selection handler
  if (onSelect) {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      onSelect(event);
    });

    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        e.stopPropagation();
        onSelect(event);
      }
    });
  }

  return el;
}
