/**
 * Technical date & timestamp formatting for operational UI
 */

export function formatUtcTime(date: Date | string | number = new Date()): string {
  const d = typeof date === "object" ? date : new Date(date);
  return d.toISOString().substring(11, 19) + " UTC";
}

export function formatUtcDateTime(date: Date | string | number = new Date()): string {
  const d = typeof date === "object" ? date : new Date(date);
  const iso = d.toISOString();
  const datePart = iso.substring(0, 10);
  const timePart = iso.substring(11, 19);
  return `${datePart} · ${timePart} UTC`;
}

export function formatRelativeSecondsAgo(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
