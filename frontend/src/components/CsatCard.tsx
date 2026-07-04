import type { Csat } from "../types";
import { BarList } from "./BarList";

interface Props {
  csat: Csat | null;
  loading: boolean;
}

export function CsatCard({ csat, loading }: Props) {
  const items = csat
    ? Object.entries(csat.response_count_by_rating)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([rating, count]) => ({
          label: `Rating ${rating}`,
          value: count,
          color: "var(--ink-3)",
        }))
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">CSAT responses</div>
        <span className="chip neutral">
          <span className="dot" />
          scale unconfirmed
        </span>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No CSAT responses in this period.</div>
      ) : (
        <BarList items={items} />
      )}
    </div>
  );
}
