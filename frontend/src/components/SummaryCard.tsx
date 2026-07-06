import type { Summary } from "../types";
import { formatHours, formatNumber, formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  summary: Summary | null;
  csatResponses: number | null;
  loading: boolean;
}

function formatDateRange(startIso: string, endIso: string): string {
  const fmt = (s: string) =>
    new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${fmt(startIso)} → ${fmt(endIso)}`;
}

export function SummaryCard({ summary, csatResponses, loading }: Props) {
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div className="card-title">This period at a glance</div>
        <div className="card-sub">
          {summary ? formatDateRange(summary.period_start, summary.period_end) : ""}
        </div>
      </div>
      <div className="stat-strip">
        {loading || !summary ? (
          Array.from({ length: 8 }).map((_, i) => <StatTileSkeleton key={i} />)
        ) : (
          <>
            <StatTile label="Tickets created" value={formatNumber(summary.tickets_created_count)} />
            <StatTile label="Tickets resolved" value={formatNumber(summary.tickets_resolved_count)} />
            <StatTile
              label="Median resolution time"
              value={formatHours(summary.median_resolution_time_hours)}
            />
            <StatTile
              label="Mean resolution time"
              value={formatHours(summary.mean_resolution_time_hours)}
            />
            <StatTile
              label="Resolved within 3 days"
              value={formatPercent(summary.resolution_within_72_hours_percentage)}
              foot="of actionable, resolved"
            />
            <StatTile
              label="Resolved over 48h"
              value={formatNumber(summary.tickets_resolved_over_48_hours_count)}
              foot={
                summary.tickets_resolved_count
                  ? `${(
                      (100 * summary.tickets_resolved_over_48_hours_count) /
                      summary.tickets_resolved_count
                    ).toFixed(0)}% of resolved`
                  : undefined
              }
            />
            <StatTile
              label="SLA breach rate"
              value={formatPercent(summary.sla_breach_percentage)}
              tone={(summary.sla_breach_percentage ?? 0) > 15 ? "warn" : "default"}
            />
            <StatTile
              label="CSAT responses"
              value={csatResponses ?? "—"}
              foot="scale unconfirmed"
            />
          </>
        )}
      </div>
    </div>
  );
}
