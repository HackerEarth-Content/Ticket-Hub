import type { BacklineOverview } from "../types";
import { formatNumber, formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";
import { RadialStat } from "./RadialStat";
import { BarList } from "./BarList";

interface Props {
  data: BacklineOverview | null;
  loading: boolean;
}

export function BacklineOverviewCard({ data, loading }: Props) {
  const resolutionItems = data
    ? Object.entries(data.final_resolution_breakdown)
        .map(([label, count]) => ({
          label,
          value: count,
          displayValue: `${formatNumber(count)} (${formatPercent(
            data.final_resolution_percentage_of_closed[label] ?? null
          )})`,
          color: "var(--accent-blue)",
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Overview</div>
          <div className="card-sub">All Support Pipeline tickets, this period</div>
        </div>
      </div>
      <div className="stat-strip" style={{ marginBottom: 18, gridTemplateColumns: "repeat(2, 1fr)" }}>
        {loading || !data ? (
          Array.from({ length: 2 }).map((_, i) => <StatTileSkeleton key={i} />)
        ) : (
          <>
            <StatTile label="Total tickets" value={formatNumber(data.total_ticket_count)} />
            <StatTile label="Still open" value={formatNumber(data.still_open_ticket_count)} />
          </>
        )}
      </div>
      <div className="radial-strip" style={{ marginBottom: 16 }}>
        {loading || !data ? (
          <div className="skeleton" style={{ height: 96, width: "100%" }} />
        ) : (
          <>
            <RadialStat
              label="Actionable"
              percentage={data.actionable_percentage}
              foot={`${formatNumber(data.actionable_ticket_count)} of total`}
            />
            <RadialStat
              label="Closed"
              percentage={data.closed_percentage_of_actionable}
              foot={`${formatNumber(data.closed_ticket_count)} tickets`}
            />
            <RadialStat
              label="Resolved by Backline"
              percentage={data.resolved_by_backline_percentage_of_actionable}
              foot={`${formatNumber(data.resolved_by_backline_count)} tickets`}
            />
            <RadialStat
              label="Escalated to Eng"
              percentage={data.escalated_to_engineering_percentage_of_actionable}
              tone="warn"
              foot={`${formatNumber(data.escalated_to_engineering_count)} tickets`}
            />
            <RadialStat
              label="FCR"
              percentage={data.fcr_percentage_of_actionable}
              tone="good"
              foot={`${formatNumber(data.fcr_true_count)} tickets`}
            />
          </>
        )}
      </div>
      {!loading && resolutionItems.length > 0 && (
        <>
          <div className="card-sub" style={{ marginBottom: 8 }}>
            Final resolution breakdown (of closed)
          </div>
          <BarList items={resolutionItems} />
        </>
      )}
    </div>
  );
}
