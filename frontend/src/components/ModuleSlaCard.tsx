import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { FrontlineFrt } from "../types";
import { api } from "../api";
import { formatPercent } from "../format";
import type { Period } from "../types";

// Same fixed categorical order as ModuleDistributionCard; neutral past the ramp.
const COLORS = [
  "var(--accent-blue)",
  "var(--accent-aqua)",
  "var(--accent-yellow)",
  "var(--accent-green)",
  "var(--accent-indigo)",
  "var(--accent-red)",
  "var(--accent-magenta)",
  "var(--accent-orange)",
];

interface Props {
  frt: FrontlineFrt | null;
  loading: boolean;
  period: Period;
}

/** FRT SLA per module: pie = each module's share of FRT-evaluated tickets,
 * table = per-module on-time/missed split and SLA %. */
export function ModuleSlaCard({ frt, loading, period }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const rows = (frt?.by_module ?? []).map((m, i) => ({
    ...m,
    total: m.on_time_count + m.missed_count,
    color: COLORS[i] ?? "var(--ink-3)",
  }));
  const grand = rows.reduce((s, r) => s + r.total, 0);
  const toggle = (m: string) =>
    setSelected((cur) => (cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m]));
  const pieRows = selected.length ? rows.filter((r) => selected.includes(r.module)) : rows;
  const sum = (rs: typeof rows) => {
    const on = rs.reduce((a, r) => a + r.on_time_count, 0);
    const missed = rs.reduce((a, r) => a + r.missed_count, 0);
    return { total: on + missed, on, missed, pct: on + missed ? (100 * on) / (on + missed) : null };
  };
  const allTotals = sum(rows);

  async function downloadExcel() {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await api.exportModuleSla(period));
    a.download = `sla-by-module-${period.replace(/:/g, "_")}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">SLA by module</div>
          <div className="card-sub">
            First-response SLA {frt ? `(${frt.sla_threshold_minutes}m)` : ""} per module · tick
            modules to consolidate and chart just those
          </div>
        </div>
        <button className="section-action" onClick={downloadExcel} disabled={loading || !rows.length}>
          ⬇️ Download Excel
        </button>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 180, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No data this period.</div>
      ) : (
        <div className="chart-columns">
          <div className="chart-col-list">
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Tickets</th>
                    <th>Share</th>
                    <th>On time</th>
                    <th>Missed</th>
                    <th>SLA %</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ fontWeight: 650 }}>
                    <td>All modules</td>
                    <td>{allTotals.total}</td>
                    <td>{formatPercent(grand ? 100 : null)}</td>
                    <td>{allTotals.on}</td>
                    <td>{allTotals.missed}</td>
                    <td>{formatPercent(allTotals.pct)}</td>
                  </tr>
                  {rows.map((r) => (
                    <tr key={r.module}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.includes(r.module)}
                          onChange={() => toggle(r.module)}
                          aria-label={`Select ${r.module}`}
                          style={{ marginRight: 8 }}
                        />
                        <span className="sw" style={{ background: r.color, marginRight: 6 }} />
                        {r.module}
                      </td>
                      <td>{r.total}</td>
                      <td>{formatPercent((100 * r.total) / grand)}</td>
                      <td>{r.on_time_count}</td>
                      <td>{r.missed_count}</td>
                      <td
                        style={{
                          fontWeight: 650,
                          color:
                            (r.on_time_percentage ?? 100) < 80
                              ? "var(--status-critical)"
                              : "var(--status-good)",
                        }}
                      >
                        {formatPercent(r.on_time_percentage)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="chart-col-chart">
            {(() => {
              const t = sum(pieRows);
              return (
                <div style={{ marginBottom: 8 }}>
                  <div className="card-sub" title={pieRows.map((r) => r.module).join(", ")}>
                    {selected.length ? pieRows.map((r) => r.module).join(", ") : "All modules"}
                  </div>
                  <div style={{ display: "flex", gap: 16, alignItems: "baseline", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 22 }}>{formatPercent(t.pct)}</strong>
                    <span className="card-sub">
                      SLA · {t.total} tickets · {t.on} on time · {t.missed} missed
                    </span>
                  </div>
                </div>
              );
            })()}
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieRows}
                  dataKey="total"
                  nameKey="module"
                  innerRadius={62}
                  outerRadius={92}
                  paddingAngle={pieRows.length > 1 ? 2 : 0}
                  cornerRadius={4}
                  isAnimationActive={false}
                >
                  {pieRows.map((r) => (
                    <Cell key={r.module} fill={r.color} stroke="var(--surface)" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }: any) =>
                    active && payload?.length ? (
                      <div className="chart-tooltip">
                        <div className="tt-title">{payload[0].payload.module}</div>
                        <div className="tt-row">
                          {payload[0].payload.total} tickets · SLA{" "}
                          {formatPercent(payload[0].payload.on_time_percentage)}
                        </div>
                      </div>
                    ) : null
                  }
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
