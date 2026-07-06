import type { ResolutionByPriority } from "../types";
import { BarList } from "./BarList";
import { formatHours } from "../format";

// Severity order -- the point is the order, not the sorted value, so this is
// an ordinal ramp (single hue) rather than categorical.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const ORDINAL_RAMP = ["var(--ord-1)", "var(--ord-2)", "var(--ord-4)", "var(--ord-5)"];

// Below this many resolved tickets, a median is just 1-2 raw values --
// one old backlog ticket closing alongside a same-day one can swing it by
// days. Flag it instead of presenting it as a stable trend.
const LOW_SAMPLE_THRESHOLD = 5;

interface Props {
  data: ResolutionByPriority | null;
  loading: boolean;
}

export function ResolutionByPriorityCard({ data, loading }: Props) {
  const byPriority = data?.median_resolution_time_hours_by_priority ?? {};
  const countByPriority = data?.resolved_ticket_count_by_priority ?? {};
  const items = PRIORITY_ORDER.filter((p) => p in byPriority).map((p, i) => ({
    label: p,
    value: byPriority[p],
    color: ORDINAL_RAMP[i],
    displayValue: formatHours(byPriority[p]),
  }));

  const lowSample = items.filter(
    (i) => (countByPriority[i.label] ?? 0) < LOW_SAMPLE_THRESHOLD
  );

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
          {lowSample.length > 0 && (
            <div className="card-sub" style={{ marginTop: 12 }}>
              Note: {lowSample
                .map((i) => `${i.label} (${countByPriority[i.label] ?? 0} resolved)`)
                .join(", ")}{" "}
              — too few tickets this period for the median to be a reliable signal.
            </div>
          )}
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
