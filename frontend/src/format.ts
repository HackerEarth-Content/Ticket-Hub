export function formatHours(hours: number | null): string {
  if (hours === null) return "—";
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export function formatPercent(pct: number | null): string {
  return pct === null ? "—" : `${pct.toFixed(1)}%`;
}

export function formatRelativeTime(iso: string | null): string {
  if (!iso) return "never synced";
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

// ponytail: portal ID is static per-portal, not worth a config layer.
const HUBSPOT_PORTAL_ID = 2586902;

/** Direct link to a ticket's record in HubSpot -- 0-5 is HubSpot's object
 * type ID for tickets, verified against this portal's own API response. */
export function hubspotTicketUrl(ticketId: string): string {
  return `https://app.hubspot.com/contacts/${HUBSPOT_PORTAL_ID}/record/0-5/${ticketId}`;
}

/** Absolute time in IST (Asia/Kolkata) -- the team's timezone -- regardless
 * of the viewer's browser locale/timezone. */
export function formatIstTime(iso: string | null): string {
  if (!iso) return "—";
  const time = new Date(iso).toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${time} IST`;
}

/** Today's calendar date in IST, as YYYY-MM-DD -- matches the backend's
 * period boundaries (resolve_period), which also key off IST, not the
 * viewer's local timezone or UTC. Using UTC here would clip the custom date
 * picker's "today" by up to 5.5h during the first stretch of the IST day. */
export function todayIstDate(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}
