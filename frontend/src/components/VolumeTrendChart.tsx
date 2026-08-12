import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Granularity, VolumeTrendPoint } from "../types";

interface Props {
  data: VolumeTrendPoint[];
  loading: boolean;
  granularity: Granularity;
}

function formatTick(iso: string, granularity: Granularity): string {
  const d = new Date(iso);
  if (granularity === "hour") {
    return d.toLocaleTimeString("en-US", { hour: "numeric", hour12: true });
  }
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function ChartTooltip({ active, payload, label, granularity }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{formatTick(label, granularity)}</div>
      {payload.map((p: any) => (
        <div className="tt-row" key={p.dataKey}>
          <span className="tt-sw" style={{ background: p.color }} />
          {p.name}: <strong style={{ color: "var(--ink)" }}>{p.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function VolumeTrendChart({ data, loading, granularity }: Props) {
  const [showTable, setShowTable] = useState(false);
  const bucketLabel = granularity === "hour" ? "Hour" : "Day";

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Ticket volume</div>
          <div className="card-sub">
            Created vs. resolved, by {granularity === "hour" ? "hour" : "day"}
          </div>
        </div>
        <button className="table-toggle" onClick={() => setShowTable((v) => !v)}>
          {showTable ? "View as chart" : "View as table"}
        </button>
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: 210, width: "100%" }} />
      ) : data.length === 0 ? (
        <div className="card-sub">No tickets in this period yet.</div>
      ) : showTable ? (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>{bucketLabel}</th>
                <th className="num">Created</th>
                <th className="num">Resolved</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.date}>
                  <td>{formatTick(d.date, granularity)}</td>
                  <td className="num">{d.tickets_created_count}</td>
                  <td className="num">{d.tickets_resolved_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fillCreated" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-blue)" stopOpacity={0.16} />
                  <stop offset="100%" stopColor="var(--accent-blue)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fillResolved" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-aqua)" stopOpacity={0.16} />
                  <stop offset="100%" stopColor="var(--accent-aqua)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="2 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => formatTick(v, granularity)}
                tick={{ fill: "var(--ink-3)", fontSize: 11 }}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                tick={{ fill: "var(--ink-3)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={32}
                allowDecimals={false}
                domain={[0, "auto"]}
              />
              <Tooltip
                content={<ChartTooltip granularity={granularity} />}
                cursor={{ stroke: "var(--line)" }}
              />
              <Area
                type="monotone"
                dataKey="tickets_created_count"
                name="Created"
                stroke="var(--accent-blue)"
                strokeWidth={2.25}
                fill="url(#fillCreated)"
                isAnimationActive={false}
                dot={
                  data.length === 1
                    ? { r: 4, strokeWidth: 2, stroke: "var(--surface)", fill: "var(--accent-blue)" }
                    : { r: 3, strokeWidth: 2, stroke: "var(--surface)", fill: "var(--accent-blue)" }
                }
                activeDot={{ r: 5 }}
              />
              <Area
                type="monotone"
                dataKey="tickets_resolved_count"
                name="Resolved"
                stroke="var(--accent-aqua)"
                strokeWidth={2.25}
                fill="url(#fillResolved)"
                isAnimationActive={false}
                dot={
                  data.length === 1
                    ? { r: 4, strokeWidth: 2, stroke: "var(--surface)", fill: "var(--accent-aqua)" }
                    : { r: 3, strokeWidth: 2, stroke: "var(--surface)", fill: "var(--accent-aqua)" }
                }
                activeDot={{ r: 5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="legend">
            <div className="item">
              <span className="sw" style={{ background: "var(--accent-blue)" }} />
              Created
            </div>
            <div className="item">
              <span className="sw" style={{ background: "var(--accent-aqua)" }} />
              Resolved
            </div>
          </div>
        </>
      )}
    </div>
  );
}
