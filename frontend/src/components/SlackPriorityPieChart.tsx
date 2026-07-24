import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Sector, Tooltip } from "recharts";

interface Props {
  data: Record<string, number>;
  activePriority: string | null;
  onSliceClick: (priority: string) => void;
  loading: boolean;
}

// Severity order/ramp -- same convention as ResolutionByPriorityCard and
// StatusDistributionCard: priority is ordinal, not categorical, so it gets
// a single-hue ramp instead of the categorical palette SlackReporterPieChart
// uses for reporters.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const ORDINAL_RAMP = ["var(--ord-1)", "var(--ord-2)", "var(--ord-4)", "var(--ord-5)"];

// Support's P-level equivalent for each derived priority -- same mapping as
// SlackPriorityCard's BarList, kept in sync so the bar rows and pie slices
// show the same label.
const P_LABEL: Record<string, string> = {
  LOW: "P3/P4",
  MEDIUM: "P2",
  HIGH: "P1",
  URGENT: "P0",
};

interface Slice {
  name: string;
  displayName: string;
  count: number;
  color: string;
}

function buildSlices(data: Record<string, number>): Slice[] {
  const known = PRIORITY_ORDER.filter((p) => data[p]).map((p, i) => ({
    name: p,
    displayName: P_LABEL[p] ? `${p} (${P_LABEL[p]})` : p,
    count: data[p],
    color: ORDINAL_RAMP[i],
  }));
  const rest = Object.keys(data).filter((p) => !PRIORITY_ORDER.includes(p));
  if (rest.length === 0) return known;
  return [
    ...known,
    {
      name: "Other",
      displayName: "Other",
      count: rest.reduce((sum, p) => sum + data[p], 0),
      color: "var(--ink-3)",
    },
  ];
}

function SliceTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const slice: Slice = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{slice.displayName}</div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: slice.color }} />
        <strong style={{ color: "var(--ink)" }}>{slice.count}</strong>&nbsp;issues
      </div>
    </div>
  );
}

// A hovered/selected slice grows outward slightly and picks up a matching-
// hue ring -- same "lift on hover, flat at rest" language SlackReporterPieChart
// and NpsDistributionPieChart use.
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

/** Distribution of Slack-reported issues by priority -- clicking a slice
 * (or a row in SlackPriorityCard's BarList, which shares `activePriority`/
 * `onSliceClick`) drills into that priority's individual tickets. */
export function SlackPriorityPieChart({ data, activePriority, onSliceClick, loading }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | undefined>(undefined);
  const slices = buildSlices(data);
  const total = slices.reduce((sum, s) => sum + s.count, 0);
  const activeIndex =
    hoverIndex ?? (activePriority ? slices.findIndex((s) => s.name === activePriority) : undefined);

  if (loading) {
    return <div className="skeleton" style={{ height: 220, width: "100%" }} />;
  }
  if (slices.length === 0) {
    return <div className="card-sub">No Slack-reported issues in this period.</div>;
  }

  return (
    <>
      <div className="donut-wrap">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={slices}
              dataKey="count"
              nameKey="name"
              innerRadius={62}
              outerRadius={92}
              paddingAngle={slices.length > 1 ? 2 : 0}
              cornerRadius={4}
              isAnimationActive={false}
              activeIndex={activeIndex}
              activeShape={renderActiveSlice}
              onMouseEnter={(_, i) => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(undefined)}
              onClick={(slice: Slice) => onSliceClick(slice.name)}
              style={{ cursor: "pointer" }}
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
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(undefined)}
            onClick={() => onSliceClick(s.name)}
            style={{ cursor: "pointer" }}
          >
            <span className="sw" style={{ background: s.color }} />
            <span className="pie-legend-name">{s.displayName}</span>
            <span className="pie-legend-count">{s.count}</span>
            <span className="pie-legend-pct">
              {total ? Math.round((s.count / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
