import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CustomerVolume, CustomerVolumeEntry } from "../types";
import { formatNumber } from "../format";

interface Props {
  data: CustomerVolume | null;
  loading: boolean;
  showAll: boolean;
  onToggleAll: (showAll: boolean) => void;
}

const ROW_HEIGHT = 30;
const MIN_CHART_HEIGHT = 90;

function VolumeTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const row: CustomerVolumeEntry = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{row.customer_name}</div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: "var(--accent-indigo)" }} />
        Tickets: <strong style={{ color: "var(--ink)" }}>{formatNumber(row.ticket_count)}</strong>
      </div>
    </div>
  );
}

/** Ranked magnitude across many accounts -- a single hue (not per-customer
 * categorical colors, these aren't distinct "series"), top-N with the long
 * tail folded into the footer counts instead of an unbounded list. */
export function CustomerVolumeCard({ data, loading, showAll, onToggleAll }: Props) {
  const [showTable, setShowTable] = useState(false);
  const rows = (showAll ? data?.all_customers : data?.top_customers) ?? [];
  const chartHeight = Math.max(MIN_CHART_HEIGHT, rows.length * ROW_HEIGHT);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Tickets by customer</div>
          <div className="card-sub">
            {showAll ? "All" : "Top"} {rows.length || ""} accounts by volume this period
          </div>
        </div>
        {rows.length > 0 && (
          <button className="table-toggle" onClick={() => setShowTable((v) => !v)}>
            {showTable ? "View as chart" : "View as table"}
          </button>
        )}
      </div>
      {loading || !data ? (
        <div className="skeleton" style={{ height: 220, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No identified customer accounts in this period.</div>
      ) : showTable ? (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th className="num">Tickets</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.customer_name}>
                  <td className="name-cell" title={r.customer_name}>
                    {r.customer_name}
                  </td>
                  <td className="num">{formatNumber(r.ticket_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
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
            <Tooltip content={<VolumeTooltip />} cursor={{ fill: "var(--surface-2)" }} />
            <Bar
              dataKey="ticket_count"
              fill="var(--accent-indigo)"
              radius={[0, 4, 4, 0]}
              maxBarSize={18}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
      {!loading && data && data.other_identified_customer_count > 0 && (
        <div className="card-sub" style={{ marginTop: 12 }}>
          <button className="table-toggle" style={{ padding: 0 }} onClick={() => onToggleAll(!showAll)}>
            {showAll
              ? "Show top 15 only"
              : `+${formatNumber(data.other_identified_customer_count)} more identified accounts (${formatNumber(
                  data.other_identified_ticket_count
                )} tickets)`}
          </button>
        </div>
      )}
    </div>
  );
}
