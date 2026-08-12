import { useState } from "react";
import type { Csat, UnmatchedCsatResponses } from "../types";
import { formatPercent } from "../format";
import { BarList } from "./BarList";

interface Props {
  csat: Csat | null;
  unmatchedCsat: UnmatchedCsatResponses | null;
  loading: boolean;
}

// Confirmed via HubSpot's hs_response_group on the CSAT survey (see
// dashboard/utils.py's get_csat): 0=Detractor, 1=Passive, 2=Promoter.
const RATING_LABELS: Record<string, string> = {
  "0": "Unhappy",
  "1": "Neutral",
  "2": "Happy",
};

function formatSubmittedAt(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function CsatCard({ csat, unmatchedCsat, loading }: Props) {
  const [showUnmatched, setShowUnmatched] = useState(false);

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
        <BarList items={items} />
      )}
      {!loading && unmatchedCsat && unmatchedCsat.unmatched_count > 0 && (
        <>
          <button
            className="table-toggle"
            style={{ marginTop: 12 }}
            onClick={() => setShowUnmatched((v) => !v)}
          >
            {showUnmatched ? "Hide" : "Show"} {unmatchedCsat.unmatched_count} unmatched response
            {unmatchedCsat.unmatched_count === 1 ? "" : "s"}
            {unmatchedCsat.truncated ? " (first 100)" : ""}
          </button>
          {showUnmatched && (
            <div className="tbl-wrap" style={{ marginTop: 8 }}>
              <table>
                <thead>
                  <tr>
                    <th>Submission</th>
                    <th>Rating</th>
                    <th>Submitted</th>
                    <th>Contact</th>
                  </tr>
                </thead>
                <tbody>
                  {unmatchedCsat.responses.map((r) => (
                    <tr key={r.submission_id}>
                      <td>#{r.submission_id}</td>
                      <td>{RATING_LABELS[String(r.rating)] ?? `Rating ${r.rating}`}</td>
                      <td>{formatSubmittedAt(r.submitted_at)}</td>
                      <td>{r.contact_id ? `#${r.contact_id}` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
