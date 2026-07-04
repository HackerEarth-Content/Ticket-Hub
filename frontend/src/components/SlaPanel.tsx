import type { SlaKpis } from "../types";
import { formatPercent } from "../format";

// Fixed status scale -- never themed, never reused for a data series.
const STATUS_COLOR: Record<string, string> = {
  "Completed on time": "var(--status-good)",
  "Completed late": "var(--status-serious)",
  "Due Soon": "var(--status-warning)",
  Overdue: "var(--status-critical)",
  "Active SLA": "var(--status-neutral)",
};
const STATUS_ORDER = ["Completed on time", "Completed late", "Due Soon", "Overdue", "Active SLA"];

function StackedBreakdown({
  title,
  breakdown,
  breachPct,
}: {
  title: string;
  breakdown: Record<string, number>;
  breachPct: number | null;
}) {
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);
  const present = STATUS_ORDER.filter((s) => breakdown[s]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 8,
        }}
      >
        <span className="card-sub">{title}</span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 650,
            color: (breachPct ?? 0) > 10 ? "var(--status-critical)" : "var(--status-good)",
          }}
        >
          {formatPercent(breachPct)} breached
        </span>
      </div>
      {total === 0 ? (
        <div className="card-sub">No data this period.</div>
      ) : (
        <>
          <div style={{ display: "flex", height: 10, borderRadius: 5, overflow: "hidden", gap: 1 }}>
            {present.map((status) => (
              <div
                key={status}
                style={{
                  width: `${(breakdown[status] / total) * 100}%`,
                  background: STATUS_COLOR[status],
                }}
                title={`${status}: ${breakdown[status]}`}
              />
            ))}
          </div>
          <div className="legend">
            {present.map((status) => (
              <div className="item" key={status}>
                <span className="sw" style={{ background: STATUS_COLOR[status] }} />
                {status === "Active SLA" ? "In progress" : status} &middot; {breakdown[status]}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

interface Props {
  sla: SlaKpis | null;
  loading: boolean;
}

export function SlaPanel({ sla, loading }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">SLA performance</div>
      </div>
      {loading || !sla ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <StackedBreakdown
            title="First response"
            breakdown={sla.first_response_sla_status_breakdown}
            breachPct={sla.first_response_sla_breach_percentage}
          />
          <StackedBreakdown
            title="Resolution"
            breakdown={sla.resolution_sla_status_breakdown}
            breachPct={sla.resolution_sla_breach_percentage}
          />
        </div>
      )}
    </div>
  );
}
