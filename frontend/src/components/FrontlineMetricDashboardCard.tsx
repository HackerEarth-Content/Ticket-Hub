import { Fragment, useState } from "react";
import type { FrontlineMetricDashboard, FrontlineMetricFormat, FrontlineMetricValues } from "../types";

interface Props {
  data: FrontlineMetricDashboard | null;
  loading: boolean;
}

function formatMetricValue(value: number | null, format: FrontlineMetricFormat): string {
  if (value === null || value === undefined) return "–";
  switch (format) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "hours":
      return `${value.toFixed(1)}h`;
    case "days":
      return `${value.toFixed(2)}d`;
    case "score":
      return value.toFixed(2);
    default:
      return value.toLocaleString("en-US");
  }
}

/** Target strings look like ">=70%", "<=72 Hrs", "6 Hrs", or "-" -- pull the
 * comparator and number back out to color the achieved cell green/red.
 * Bare-number targets (NPS score/mean) are informational only, no color. */
function toneForTarget(value: number | null, target: string): "good" | "critical" | "default" {
  if (value === null) return "default";
  const match = target.match(/^(>=|<=)\s*(-?\d+(?:\.\d+)?)/);
  if (!match) return "default";
  const [, op, numStr] = match;
  const threshold = parseFloat(numStr);
  if (op === ">=") return value >= threshold ? "good" : "critical";
  return value <= threshold ? "good" : "critical";
}

export function FrontlineMetricDashboardCard({ data, loading }: Props) {
  const [activeGroup, setActiveGroup] = useState<string | null>(null);

  if (loading || !data) {
    return (
      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Frontline Metric Dashboard</div>
            <div className="card-sub">Live quarterly rollup of frontline KPIs</div>
          </div>
        </div>
        <div className="skeleton" style={{ height: 220 }} />
      </div>
    );
  }

  const groupKey = activeGroup ?? data.groups[0]?.key;
  const group = data.groups.find((g) => g.key === groupKey) ?? data.groups[0];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Frontline Metric Dashboard</div>
          <div className="card-sub">
            Live quarterly rollup, computed straight off current ticket data -- scroll to see every quarter
          </div>
        </div>
      </div>

      <div className="fmd-group-nav">
        {data.groups.map((g) => (
          <button
            key={g.key}
            className={`fmd-group-btn ${g.key === group.key ? "active" : ""}`}
            onClick={() => setActiveGroup(g.key)}
          >
            {g.label}
          </button>
        ))}
      </div>

      <div className="tbl-wrap">
        <table className="fmd-table">
          <thead>
            <tr>
              <th className="fmd-sticky-col"></th>
              {data.quarters.map((q) => (
                <th key={q.code} className="fmd-quarter-head" colSpan={5}>
                  {q.label}
                </th>
              ))}
            </tr>
            <tr>
              <th className="fmd-sticky-col">Metric</th>
              {data.quarters.map((q) => (
                <Fragment key={q.code}>
                  <th className="num fmd-quarter-start">Target</th>
                  {q.month_labels.map((label, i) => (
                    <th key={i} className="num">
                      {label}
                    </th>
                  ))}
                  <th className="num">Achieved</th>
                </Fragment>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.metrics.map((metric) => (
              <tr key={metric.key}>
                <td className="fmd-sticky-col">{metric.label}</td>
                {data.quarters.map((q) => {
                  const achievedValue = (q.achieved as FrontlineMetricValues)[metric.key] ?? null;
                  const tone = toneForTarget(achievedValue, metric.target);
                  return (
                    <Fragment key={q.code}>
                      <td className="num fmd-quarter-start">{metric.target}</td>
                      {q.months.map((month, i) => (
                        <td key={i} className="num">
                          {formatMetricValue(month[metric.key] ?? null, metric.format)}
                        </td>
                      ))}
                      <td className={`num fmd-achieved fmd-${tone}`}>
                        {formatMetricValue(achievedValue, metric.format)}
                      </td>
                    </Fragment>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
