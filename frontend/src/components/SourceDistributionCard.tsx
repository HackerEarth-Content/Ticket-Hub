import type { SourceDistribution } from "../types";
import { BarList } from "./BarList";

// Fixed categorical order -- same slots ModuleDistributionCard uses, so a
// channel and a module never accidentally share a color story.
const CATEGORICAL_SLOTS = [
  "var(--accent-blue)",
  "var(--accent-aqua)",
  "var(--accent-yellow)",
  "var(--accent-green)",
  "var(--accent-indigo)",
];

interface Props {
  distribution: SourceDistribution | null;
  loading: boolean;
}

export function SourceDistributionCard({ distribution, loading }: Props) {
  const entries = Object.entries(distribution?.by_source ?? {}).sort((a, b) => b[1] - a[1]);
  const items = entries.map(([label, value], i) => ({
    label,
    value,
    color: CATEGORICAL_SLOTS[i % CATEGORICAL_SLOTS.length],
  }));

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Volume by source</div>
          <div className="card-sub">Which channel tickets came in through, this period</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No tickets in this period yet.</div>
      ) : (
        <BarList items={items} />
      )}
    </div>
  );
}
