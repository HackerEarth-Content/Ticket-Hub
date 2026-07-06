interface Props {
  label: string;
  percentage: number | null;
  foot?: string;
  tone?: "default" | "good" | "warn";
}

const SIZE = 64;
const STROKE = 6;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const TONE_COLOR: Record<NonNullable<Props["tone"]>, string> = {
  default: "var(--accent-blue)",
  good: "var(--status-good)",
  warn: "var(--status-critical)",
};

/** Ring progress indicator for ratio-style KPIs (percent of a whole), so a
 * rate reads at a glance instead of as one more number in a stat grid. */
export function RadialStat({ label, percentage, foot, tone = "default" }: Props) {
  const clamped = percentage === null ? null : Math.min(Math.max(percentage, 0), 100);
  const offset = clamped === null ? CIRCUMFERENCE : CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div className="radial-stat">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <circle cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" stroke="var(--surface-2)" strokeWidth={STROKE} />
        {clamped !== null && (
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={TONE_COLOR[tone]}
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
          />
        )}
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="radial-stat-value">
          {clamped === null ? "—" : `${Math.round(clamped)}%`}
        </text>
      </svg>
      <div className="radial-stat-label">{label}</div>
      {foot && <div className="radial-stat-foot">{foot}</div>}
    </div>
  );
}
