import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Sector, Tooltip } from "recharts";
import type { NpsBucket } from "../types";

interface Props {
  promoterCount: number;
  passiveCount: number;
  detractorCount: number;
  activeBucket: NpsBucket | null;
  onSliceClick: (bucket: NpsBucket) => void;
  loading: boolean;
}

// Promoter -> Passive -> Detractor reads as "good to concerning", same
// light-to-dark ordinal ramp ResolutionByPriorityCard/SlackPriorityPieChart
// use for severity -- skipping ord-2/ord-4 for stronger contrast across
// only 3 slices.
const BUCKETS: { key: NpsBucket; name: string; color: string }[] = [
  { key: "promoter", name: "Promoters", color: "var(--ord-1)" },
  { key: "passive", name: "Passives", color: "var(--ord-3)" },
  { key: "detractor", name: "Detractors", color: "var(--ord-5)" },
];

interface Slice {
  key: NpsBucket;
  name: string;
  count: number;
  color: string;
}

function SliceTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const slice: Slice = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{slice.name}</div>
      <div className="tt-row">
        <span className="tt-sw" style={{ background: slice.color }} />
        <strong style={{ color: "var(--ink)" }}>{slice.count}</strong>&nbsp;responses
      </div>
    </div>
  );
}

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

/** Distribution of NPS reviews by bucket -- clicking a slice (or a row in
 * NpsCard's BarList, which shares `activeBucket`/`onSliceClick`) drills into
 * that bucket's individual responses. */
export function NpsDistributionPieChart({
  promoterCount,
  passiveCount,
  detractorCount,
  activeBucket,
  onSliceClick,
  loading,
}: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | undefined>(undefined);
  const countByBucket: Record<NpsBucket, number> = {
    promoter: promoterCount,
    passive: passiveCount,
    detractor: detractorCount,
  };
  const slices: Slice[] = BUCKETS.filter((b) => countByBucket[b.key] > 0).map((b) => ({
    key: b.key,
    name: b.name,
    count: countByBucket[b.key],
    color: b.color,
  }));
  const total = slices.reduce((sum, s) => sum + s.count, 0);
  const activeIndex =
    hoverIndex ?? (activeBucket ? slices.findIndex((s) => s.key === activeBucket) : undefined);

  if (loading) {
    return <div className="skeleton" style={{ height: 220, width: "100%" }} />;
  }
  if (slices.length === 0) {
    return <div className="card-sub">No NPS responses in this period.</div>;
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
              onClick={(slice: Slice) => onSliceClick(slice.key)}
              style={{ cursor: "pointer" }}
            >
              {slices.map((s) => (
                <Cell key={s.key} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
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
            key={s.key}
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(undefined)}
            onClick={() => onSliceClick(s.key)}
            style={{ cursor: "pointer" }}
          >
            <span className="sw" style={{ background: s.color }} />
            <span className="pie-legend-name">{s.name}</span>
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
