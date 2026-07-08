import { useState } from "react";
import type { DataQuality, UncategorizedTickets } from "../types";
import { formatPercent, hubspotTicketUrl } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  dataQuality: DataQuality | null;
  uncategorized: UncategorizedTickets | null;
  loading: boolean;
}

export function DataQualityCard({ dataQuality, uncategorized, loading }: Props) {
  const [showUncategorized, setShowUncategorized] = useState(false);

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">Data quality</div>
      </div>
      <div className="stat-strip" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {loading || !dataQuality ? (
          <>
            <StatTileSkeleton />
            <StatTileSkeleton />
          </>
        ) : (
          <>
            <StatTile
              label="Priority inferred"
              value={formatPercent(dataQuality.priority_inferred_percentage)}
              foot="real field mostly blank"
            />
            <StatTile
              label="Uncategorized"
              value={formatPercent(dataQuality.uncategorized_ticket_percentage)}
              foot="of solved/closed tickets"
            />
          </>
        )}
      </div>
      {!loading && uncategorized && uncategorized.uncategorized_count > 0 && (
        <>
          <button
            className="table-toggle"
            style={{ marginTop: 12 }}
            onClick={() => setShowUncategorized((v) => !v)}
          >
            {showUncategorized ? "Hide" : "Show"} {uncategorized.uncategorized_count} resolved
            uncategorized ticket{uncategorized.uncategorized_count === 1 ? "" : "s"}
            {uncategorized.truncated ? " (first 100)" : ""}
          </button>
          {showUncategorized && (
            <div className="tbl-wrap" style={{ marginTop: 8 }}>
              <table>
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Owner</th>
                    <th>Final resolution</th>
                  </tr>
                </thead>
                <tbody>
                  {uncategorized.tickets.map((t) => (
                    <tr key={t.ticket_id}>
                      <td className="name-cell" title={t.subject}>
                        <a href={hubspotTicketUrl(t.ticket_id)} target="_blank" rel="noopener noreferrer">
                          {t.subject || t.ticket_id}
                        </a>
                        <div className="card-sub">#{t.ticket_id}</div>
                      </td>
                      <td>{t.owner_name ?? "—"}</td>
                      <td>{t.final_resolution ?? "—"}</td>
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
