import type { SlackIssues } from "../types";
import { formatNumber } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  data: SlackIssues | null;
  loading: boolean;
}

/** Headline numbers for the Content/engg On-call tab -- total Slack-reported
 * issues plus the per-team split, same at-a-glance strip pattern as
 * CustomerOverviewCard. */
export function SlackOverviewCard({ data, loading }: Props) {
  const byCategory = data?.tickets_by_workflow_category;
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div>
          <div className="card-title">Slack issues at a glance</div>
          <div className="card-sub">Tickets reported through the Slack source this period</div>
        </div>
      </div>
      <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        {loading || !data ? (
          Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)
        ) : (
          <>
            <StatTile label="Total issues" value={formatNumber(data.issue_count)} />
            <StatTile label="Content" value={formatNumber(byCategory?.content.count ?? 0)} />
            <StatTile label="Engg Oncall" value={formatNumber(byCategory?.engg_oncall.count ?? 0)} />
            <StatTile
              label="Uncategorized"
              value={formatNumber(byCategory?.uncategorized.count ?? 0)}
              foot="no workflow tag"
            />
          </>
        )}
      </div>
    </div>
  );
}
