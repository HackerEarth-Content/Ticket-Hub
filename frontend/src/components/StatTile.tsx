interface Props {
  label: string;
  value: string | number;
  unit?: string;
  tone?: "default" | "warn" | "good" | "critical";
  foot?: string;
}

export function StatTile({ label, value, unit, tone = "default", foot }: Props) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className={`value ${tone !== "default" ? tone : ""}`}>
        {value}
        {unit ? <span className="unit">{unit}</span> : null}
      </div>
      {foot ? <div className="foot">{foot}</div> : null}
    </div>
  );
}

export function StatTileSkeleton() {
  return (
    <div className="stat">
      <div className="skeleton" style={{ width: "60%", height: 11, marginBottom: 8 }} />
      <div className="skeleton" style={{ width: "40%", height: 22 }} />
    </div>
  );
}
