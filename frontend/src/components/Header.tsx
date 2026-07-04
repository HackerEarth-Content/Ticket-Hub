import type { Period, SyncStatus } from "../types";
import { formatIstTime, formatNumber, formatRelativeTime } from "../format";

const PERIODS: { key: Period; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
];

interface Props {
  period: Period;
  onPeriodChange: (p: Period) => void;
  sync: SyncStatus | null;
  syncing: boolean;
  syncError: string | null;
  onSyncNow: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export function Header({
  period,
  onPeriodChange,
  sync,
  syncing,
  syncError,
  onSyncNow,
  theme,
  onToggleTheme,
}: Props) {
  const stale = sync?.last_synced_at
    ? Date.now() - new Date(sync.last_synced_at).getTime() > 30 * 60_000
    : false;

  return (
    <header className="top">
      <div className="brand">
        <div className="mark">H</div>
        <div>
          <div className="eyebrow">HackerEarth &middot; Support</div>
          <h1>Helpdesk Operations</h1>
        </div>
      </div>
      <div className="toolbar">
        <div className="sync-chip" title={syncError ?? undefined}>
          <span className={`sync-dot ${stale || syncError ? "stale" : ""}`} />
          {sync
            ? `Synced ${formatRelativeTime(sync.last_synced_at)} (${formatIstTime(
                sync.last_synced_at
              )}) · ${formatNumber(sync.total_ticket_count)} tickets`
            : "Connecting…"}
        </div>
        <button
          className="icon-btn"
          onClick={onSyncNow}
          disabled={syncing}
          aria-label="Sync now"
          title="Sync now"
        >
          {syncing ? "⏳" : "🔄"}
        </button>
        <div className="period-group" role="group" aria-label="Date range">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              className={period === p.key ? "active" : ""}
              onClick={() => onPeriodChange(p.key)}
              aria-pressed={period === p.key}
            >
              {p.label}
            </button>
          ))}
        </div>
        <button
          className="icon-btn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? "🌙" : "☀️"}
        </button>
      </div>
    </header>
  );
}
