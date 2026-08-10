import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EventVolume, EventVolumeEntry } from "../types";
import { formatNumber } from "../format";

interface Props {
  data: EventVolume | null;
  loading: boolean;
}

const ROW_HEIGHT = 44;
const MIN_CHART_HEIGHT = 90;

function VolumeTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const row: EventVolumeEntry = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{row.event_name}</div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: "var(--accent-yellow)" }} />
        Issues: <strong style={{ color: "var(--ink)" }}>{formatNumber(row.ticket_count)}</strong>
      </div>
    </div>
  );
}

/** Every event with issues in the selected period, ranked by issue count --
 * the list itself is already period-scoped (get_event_ticket_volume), so an
 * event with zero issues this period simply isn't in the data to begin with. */
export function EventsCard({ data, loading }: Props) {
  const [showTable, setShowTable] = useState(false);

  const rows = data?.events ?? [];
  const chartHeight = Math.max(MIN_CHART_HEIGHT, rows.length * ROW_HEIGHT);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Issues by event</div>
          <div className="card-sub">{rows.length} event(s) with issues this period</div>
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
        <div className="card-sub">No events with issues in this period.</div>
      ) : showTable ? (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th className="num">Issues</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.event_name}>
                  <td className="name-cell" title={r.event_name}>
                    {r.event_name}
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
              dataKey="event_name"
              width={220}
              tick={{ fill: "var(--ink-2)", fontSize: 11.5 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<VolumeTooltip />} cursor={{ fill: "var(--surface-2)" }} />
            <Bar
              dataKey="ticket_count"
              fill="var(--accent-yellow)"
              radius={[0, 4, 4, 0]}
              maxBarSize={22}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
