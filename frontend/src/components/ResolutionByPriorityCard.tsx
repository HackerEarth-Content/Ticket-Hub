import type { ResolutionByPriority } from "../types";
import { BarList } from "./BarList";
import { formatHours } from "../format";

// Severity order -- the point is the order, not the sorted value, so this is
// an ordinal ramp (single hue) rather than categorical.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const ORDINAL_RAMP = ["var(--ord-1)", "var(--ord-2)", "var(--ord-4)", "var(--ord-5)"];

interface Props {
  data: ResolutionByPriority | null;
  loading: boolean;
}

export function ResolutionByPriorityCard({ data, loading }: Props) {
  const byPriority = data?.median_resolution_time_hours_by_priority ?? {};
  const items = PRIORITY_ORDER.filter((p) => p in byPriority).map((p, i) => ({
    label: p,
    value: byPriority[p],
    color: ORDINAL_RAMP[i],
    displayValue: formatHours(byPriority[p]),
  }));

  const urgentSlowerThanHigh =
    byPriority.URGENT !== undefined &&
    byPriority.HIGH !== undefined &&
    byPriority.URGENT > byPriority.HIGH;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Median resolution time, by priority</div>
          <div className="card-sub">Ordered by severity, not by value</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 120, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No resolved tickets with priority in this period.</div>
      ) : (
        <>
          <BarList items={items} maxValue={Math.max(...items.map((i) => i.value))} />
          {urgentSlowerThanHigh && (
            <div className="card-sub" style={{ marginTop: 12 }}>
              Note: URGENT resolves slower than HIGH — worth a look, not a chart bug.
            </div>
          )}
        </>
      )}
    </div>
  );
}
