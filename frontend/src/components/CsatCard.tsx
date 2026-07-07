import type { Csat } from "../types";
import { formatPercent } from "../format";
import { BarList } from "./BarList";

interface Props {
  csat: Csat | null;
  loading: boolean;
}

// Confirmed via HubSpot's hs_response_group on the CSAT survey (see
// dashboard/utils.py's get_csat): 0=Detractor, 1=Passive, 2=Promoter.
const RATING_LABELS: Record<string, string> = {
  "0": "Dissatisfied",
  "1": "Neutral",
  "2": "Satisfied",
};

export function CsatCard({ csat, loading }: Props) {
  const items = csat
    ? Object.entries(csat.response_count_by_rating)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([rating, count]) => ({
          label: RATING_LABELS[rating] ?? `Rating ${rating}`,
          value: count,
          color: "var(--ink-3)",
        }))
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">CSAT responses</div>
          {csat && csat.normalized_csat_percentage !== null && (
            <div className="card-sub">
              Normalized CSAT: {formatPercent(csat.normalized_csat_percentage)}
            </div>
          )}
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No CSAT responses in this period.</div>
      ) : (
        <>
          <BarList items={items} />
          {csat && csat.unmatched_to_ticket_count > 0 && (
            <div className="card-sub" style={{ marginTop: 10 }}>
              {csat.unmatched_to_ticket_count} response(s) couldn't be matched to a ticket
            </div>
          )}
        </>
      )}
    </div>
  );
}
