import type { Nps } from "../types";
import { BarList } from "./BarList";

interface Props {
  nps: Nps | null;
  loading: boolean;
}

export function NpsCard({ nps, loading }: Props) {
  const items = nps
    ? [
        { label: "Promoters", value: nps.promoter_count, color: "var(--ink-3)" },
        { label: "Passives", value: nps.passive_count, color: "var(--ink-3)" },
        { label: "Detractors", value: nps.detractor_count, color: "var(--ink-3)" },
      ]
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">NPS responses</div>
          {nps && nps.nps_score !== null && (
            <div className="card-sub">NPS score: {nps.nps_score}</div>
          )}
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : !nps || nps.total_response_count === 0 ? (
        <div className="card-sub">No NPS responses in this period.</div>
      ) : (
        <BarList items={items} />
      )}
    </div>
  );
}
