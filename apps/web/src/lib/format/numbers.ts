/**
 * Technical metric and numerical formatting for operational UI
 */

export function formatPercent(value: number, decimals: number = 0): string {
  const safeVal = typeof value === "number" && !isNaN(value) && isFinite(value) ? value : 0;
  const pct = safeVal <= 1 ? safeVal * 100 : safeVal;
  return `${pct.toFixed(decimals)}%`;
}

export function formatFrp(mw: number): string {
  const safeMw = typeof mw === "number" && !isNaN(mw) && isFinite(mw) ? mw : 0;
  if (safeMw >= 1000) {
    return `${(safeMw / 1000).toFixed(2)} GW`;
  }
  return `${safeMw.toFixed(1)} MW`;
}

export function formatCompactCount(count: number): string {
  const safeCount = typeof count === "number" && !isNaN(count) && isFinite(count) ? count : 0;
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(safeCount);
}
