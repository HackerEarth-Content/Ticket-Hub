import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Sector, Tooltip } from "recharts";
import type { SlackReporterCounts } from "../types";
import { formatNumber } from "../format";

interface Props {
  data: SlackReporterCounts[];
  loading: boolean;
  title?: string;
  emptyLabel?: string;
}

// Fixed categorical order -- validated for CVD-safe adjacency, same order
// ModuleDistributionCard/SourceDistributionCard use. Never cycled, never
// reassigned by value.
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

interface Slice {
  name: string;
  reported_count: number;
  solved_count: number;
  color: string;
}

function buildSlices(data: SlackReporterCounts[]): Slice[] {
  const sorted = [...data].sort((a, b) => b.reported_count - a.reported_count);
  const toSlice = (r: SlackReporterCounts, i: number): Slice => ({
    name: r.reporter_name,
    reported_count: r.reported_count,
    solved_count: r.solved_count,
    color: CATEGORICAL_SLOTS[i],
  });

  if (sorted.length <= MAX_SLOTS) {
    return sorted.map(toSlice);
  }

  // Series-count ladder: past 8, fold the tail into "Other" rather than
  // generating a 9th hue (indistinguishable under CVD anyway).
  const head = sorted.slice(0, MAX_SLOTS - 1).map(toSlice);
  const tail = sorted.slice(MAX_SLOTS - 1);
  head.push({
    name: "Other",
    reported_count: tail.reduce((sum, r) => sum + r.reported_count, 0),
    solved_count: tail.reduce((sum, r) => sum + r.solved_count, 0),
    color: CATEGORICAL_SLOTS[MAX_SLOTS - 1],
  });
  return head;
}

function SliceTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const slice: Slice = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{slice.name}</div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: slice.color }} />
        <strong style={{ color: "var(--ink)" }}>{slice.solved_count}</strong>&nbsp;issues solved
      </div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: slice.color }} />
        <strong style={{ color: "var(--ink)" }}>{slice.reported_count}</strong>&nbsp;issues reported
      </div>
    </div>
  );
}

// A hovered slice grows outward slightly and picks up a matching-hue ring --
// the same "lift on hover, flat at rest" language as .card, applied to a mark.
function renderActiveSlice(props: any) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 5}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        cornerRadius={4}
      />
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={outerRadius + 8}
        outerRadius={outerRadius + 10}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        opacity={0.35}
      />
    </g>
  );
}

/** Part-to-whole by reporter would normally be a stacked bar (see dataviz
 * guidance), but a pie was requested specifically -- kept legible by
 * capping at 8 slices (same series-count ladder as ModuleDistributionCard)
 * and folding the long tail into "Other" rather than generating more hues. */
export function SlackReporterPieChart({
  data,
  loading,
  title = "Issues by reporter",
  emptyLabel = "No Slack-reported issues in this period.",
}: Props) {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const slices = buildSlices(data);
  const total = slices.reduce((sum, s) => sum + s.reported_count, 0);
  const totalSolved = slices.reduce((sum, s) => sum + s.solved_count, 0);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">{title}</div>
          <div className="card-sub">
            {slices.length > MAX_SLOTS - 1
              ? `Top ${MAX_SLOTS - 1}, tail folded into Other`
              : "Who's reporting Slack issues"}
            {` · ${formatNumber(total)} issue${total === 1 ? "" : "s"} total`}
            {` · ${formatNumber(totalSolved)} closed`}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 220, width: "100%" }} />
      ) : slices.length === 0 ? (
        <div className="card-sub">{emptyLabel}</div>
      ) : (
        <>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={slices}
                  dataKey="reported_count"
                  nameKey="name"
                  innerRadius={62}
                  outerRadius={92}
                  paddingAngle={slices.length > 1 ? 2 : 0}
                  cornerRadius={4}
                  isAnimationActive={false}
                  activeIndex={activeIndex}
                  activeShape={renderActiveSlice}
                  onMouseEnter={(_, i) => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(undefined)}
                >
                  {slices.map((s) => (
                    <Cell key={s.name} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip content={<SliceTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="pie-legend">
            {slices.map((s, i) => (
              <div
                className={`pie-legend-row ${activeIndex === i ? "active" : ""}`}
                key={s.name}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseLeave={() => setActiveIndex(undefined)}
              >
                <span className="sw" style={{ background: s.color }} />
                <span className="pie-legend-name">{s.name}</span>
                <span className="pie-legend-count">{s.reported_count}</span>
                <span className="pie-legend-pct">
                  {total ? Math.round((s.reported_count / total) * 100) : 0}%
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
