import { Fragment, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber } from "../format";

type Entry = { customer_name: string } & Record<string, unknown>;

interface Props {
  title: string;
  sub: string;
  // Dynamic keyed access below (counts[countsKey], etc.) is inherently
  // untyped -- callers pass their own concrete entry type, which TS won't
  // structurally match against an indexed type, so this stays loose by design.
  customers: any[];
  loading: boolean;
  /** Field on each entry holding the Record<string, number> to stack/chart. */
  countsKey: string;
  /** Optional second Record<string, number> field shown as an expandable
   * per-row detail (e.g. stage-level detail under a status breakdown). */
  drilldownKey?: string;
  drilldownLabel?: string;
  emptyLabel?: string;
}

// Fixed hue order (this dashboard's existing brand accents) -- a category
// always gets the same color across every row and the legend, in every
// render, regardless of which categories happen to appear this period.
const ACCENT_ROSTER = [
  "var(--accent-blue)",
  "var(--accent-aqua)",
  "var(--accent-orange)",
  "var(--accent-magenta)",
  "var(--accent-indigo)",
  "var(--accent-yellow)",
  "var(--accent-red)",
  "var(--accent-green)",
];

const ROW_HEIGHT = 34;
const MIN_CHART_HEIGHT = 90;

function counts(entry: Entry, key: string): Record<string, number> {
  return (entry[key] as Record<string, number>) ?? {};
}

function total(counts: Record<string, number>): number {
  return Object.values(counts).reduce((a, b) => a + b, 0);
}

function BreakdownTooltip({ active, payload, allKeys, colorFor, byName, countsKey, drilldownKey, drilldownLabel }: any) {
  if (!active || !payload?.length) return null;
  const name = payload[0]?.payload?.customer_name;
  const entry: Entry | undefined = byName[name];
  if (!entry) return null;
  const rowCounts = counts(entry, countsKey);
  const rowTotal = total(rowCounts);
  const drilldown = drilldownKey ? counts(entry, drilldownKey) : null;
  const topDrilldown = drilldown
    ? Object.entries(drilldown).sort((a, b) => b[1] - a[1])[0]
    : null;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{name}</div>
      {allKeys
        .filter((k: string) => rowCounts[k])
        .map((k: string) => (
          <div className="tt-row" key={k}>
            <span className="tt-sw" style={{ background: colorFor(k) }} />
            {k}: <strong style={{ color: "var(--ink)" }}>{formatNumber(rowCounts[k])}</strong>
          </div>
        ))}
      <div className="tt-row" style={{ marginTop: 4, borderTop: "1px solid var(--line)", paddingTop: 4 }}>
        Total: <strong style={{ color: "var(--ink)" }}>{formatNumber(rowTotal)}</strong>
      </div>
      {topDrilldown && (
        <div className="tt-row" style={{ color: "var(--ink-3)", marginTop: 2 }}>
          Top {drilldownLabel?.toLowerCase()}: {topDrilldown[0]} ({topDrilldown[1]})
        </div>
      )}
    </div>
  );
}

/** Part-to-whole per customer -> horizontal stacked bar, categorical color
 * (a handful of fixed categories, so identity coloring is correct here,
 * unlike a single-hue ranked-magnitude chart). Shared by every "breakdown by
 * customer" card on the Customers tab so the chart/table/tooltip machinery
 * exists exactly once. */
export function StackedBreakdownCard({
  title,
  sub,
  customers,
  loading,
  countsKey,
  drilldownKey,
  drilldownLabel = "detail",
  emptyLabel = "No identified customer accounts in this period.",
}: Props) {
  const [showTable, setShowTable] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const allKeys = Array.from(
    new Set(customers.flatMap((c) => Object.keys(counts(c, countsKey))))
  ).sort();
  const colorFor = (key: string) => ACCENT_ROSTER[allKeys.indexOf(key) % ACCENT_ROSTER.length];
  const byName = Object.fromEntries(customers.map((c) => [c.customer_name, c]));
  const chartData = customers.map((c) => ({ customer_name: c.customer_name, ...counts(c, countsKey) }));
  const chartHeight = Math.max(MIN_CHART_HEIGHT, customers.length * ROW_HEIGHT);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">{title}</div>
          <div className="card-sub">{sub}</div>
        </div>
        {customers.length > 0 && (
          <button className="table-toggle" onClick={() => setShowTable((v) => !v)}>
            {showTable ? "View as chart" : "View as table"}
          </button>
        )}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 220, width: "100%" }} />
      ) : customers.length === 0 ? (
        <div className="card-sub">{emptyLabel}</div>
      ) : showTable ? (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                {allKeys.map((k) => (
                  <th className="num" key={k}>
                    {k}
                  </th>
                ))}
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => {
                const rowCounts = counts(c, countsKey);
                const drilldown = drilldownKey ? counts(c, drilldownKey) : null;
                return (
                  <Fragment key={c.customer_name}>
                    <tr>
                      <td>
                        {drilldown ? (
                          <button
                            className="table-toggle"
                            onClick={() =>
                              setExpandedRow(expandedRow === c.customer_name ? null : c.customer_name)
                            }
                          >
                            {c.customer_name}
                          </button>
                        ) : (
                          c.customer_name
                        )}
                      </td>
                      {allKeys.map((k) => (
                        <td className="num" key={k}>
                          {rowCounts[k] ? formatNumber(rowCounts[k]) : "—"}
                        </td>
                      ))}
                      <td className="num">{formatNumber(total(rowCounts))}</td>
                    </tr>
                    {drilldown && expandedRow === c.customer_name && (
                      <tr>
                        <td colSpan={allKeys.length + 2} style={{ background: "var(--surface-2)" }}>
                          <span className="card-sub">
                            By {drilldownLabel}:{" "}
                            {Object.entries(drilldown)
                              .sort((a, b) => b[1] - a[1])
                              .map(([k, count]) => `${k} (${formatNumber(count)})`)
                              .join(", ")}
                          </span>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          {allKeys.length > 1 && (
            <div className="legend" style={{ marginBottom: 10 }}>
              {allKeys.map((k) => (
                <div className="item" key={k}>
                  <span className="sw" style={{ background: colorFor(k) }} />
                  {k}
                </div>
              ))}
            </div>
          )}
          <ResponsiveContainer width="100%" height={chartHeight}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke="var(--line)" strokeDasharray="2 3" />
              <XAxis
                type="number"
                tick={{ fill: "var(--ink-3)", fontSize: 11 }}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="customer_name"
                width={140}
                tick={{ fill: "var(--ink-2)", fontSize: 11.5 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={
                  <BreakdownTooltip
                    allKeys={allKeys}
                    colorFor={colorFor}
                    byName={byName}
                    countsKey={countsKey}
                    drilldownKey={drilldownKey}
                    drilldownLabel={drilldownLabel}
                  />
                }
                cursor={{ fill: "var(--surface-2)" }}
              />
              {allKeys.map((k) => (
                <Bar
                  key={k}
                  dataKey={k}
                  stackId="breakdown"
                  fill={colorFor(k)}
                  maxBarSize={18}
                  isAnimationActive={false}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
