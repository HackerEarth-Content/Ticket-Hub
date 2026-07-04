import type { ModuleDistribution } from "../types";
import { BarList } from "./BarList";

// Fixed categorical order -- validated for CVD-safe adjacency (see color report).
// Never cycled, never reassigned by value.
const CATEGORICAL_SLOTS = [
  "var(--accent-blue)",
  "var(--accent-aqua)",
  "var(--accent-yellow)",
  "var(--accent-green)",
  "var(--accent-indigo)",
  "var(--accent-red)",
  "var(--accent-magenta)",
  "var(--accent-orange)",
];
const MAX_SLOTS = 8;

interface Props {
  distribution: ModuleDistribution | null;
  loading: boolean;
}

export function ModuleDistributionCard({ distribution, loading }: Props) {
  const items = buildItems(distribution);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Volume by module</div>
          <div className="card-sub">
            {items.length > MAX_SLOTS - 1
              ? `Top ${MAX_SLOTS - 1}, tail folded into Other`
              : "All modules this period"}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 180, width: "100%" }} />
      ) : (
        <BarList items={items} />
      )}
    </div>
  );
}

function buildItems(distribution: ModuleDistribution | null) {
  if (!distribution) return [];
  const entries = Object.entries(distribution.ticket_count_by_module).sort(
    (a, b) => b[1] - a[1]
  );

  if (entries.length <= MAX_SLOTS) {
    return entries.map(([label, value], i) => ({
      label,
      value,
      color: CATEGORICAL_SLOTS[i],
    }));
  }

  // Series-count ladder: past 8, fold the tail into "Other" rather than
  // generating a 9th hue (indistinguishable under CVD anyway).
  const head = entries.slice(0, MAX_SLOTS - 1);
  const tail = entries.slice(MAX_SLOTS - 1);
  const otherExisting = tail.find(([label]) => label === "Other");
  const otherTotal = tail.reduce((sum, [, v]) => sum + v, 0);

  const items = head.map(([label, value], i) => ({
    label,
    value,
    color: CATEGORICAL_SLOTS[i],
  }));
  items.push({
    label: otherExisting ? "Other" : "Other (combined)",
    value: otherTotal,
    color: CATEGORICAL_SLOTS[MAX_SLOTS - 1],
  });
  return items;
}
