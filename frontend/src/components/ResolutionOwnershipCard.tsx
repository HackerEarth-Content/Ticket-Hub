import type { ResolutionOwnership } from "../types";
import { BarList } from "./BarList";
import { formatPercent } from "../format";

// Categorical -- buckets are distinct owners of the resolution, not a scale.
const BUCKET_COLOR: Record<string, string> = {
  Support: "var(--accent-blue)",
  Engineering: "var(--accent-indigo)",
  "Backline Engineering": "var(--accent-aqua)",
  QA: "var(--accent-yellow)",
  Content: "var(--accent-magenta)",
  Programs: "var(--accent-orange)",
  Marketing: "var(--accent-green)",
  Finance: "var(--accent-red)",
  Automation: "var(--ink-3)",
};
const FALLBACK_COLOR = "var(--status-neutral)";

interface Props {
  data: ResolutionOwnership | null;
  loading: boolean;
}

export function ResolutionOwnershipCard({ data, loading }: Props) {
  const percentages = data?.percentage_of_resolved_by_bucket ?? {};
  const items = Object.entries(percentages)
    .filter(([, pct]) => pct !== null)
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
    .map(([bucket, pct]) => ({
      label: bucket,
      value: pct ?? 0,
      color: BUCKET_COLOR[bucket] ?? FALLBACK_COLOR,
      displayValue: formatPercent(pct),
    }));

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Who resolves tickets</div>
          <div className="card-sub">Share of resolved tickets, by final resolution owner</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 120, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No resolved tickets in this period.</div>
      ) : (
        <BarList items={items} maxValue={100} />
      )}
    </div>
  );
}
