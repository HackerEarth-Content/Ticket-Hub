import { useState } from "react";
import type { DataAnomalies } from "../types";
import { formatNumber } from "../format";

interface Props {
  data: DataAnomalies | null;
  loading: boolean;
}

export function AnomaliesCard({ data, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const groups = Object.entries(data?.anomalies_by_type ?? {}).filter(([, g]) => g.count > 0);

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Data anomalies</div>
          <div className="card-sub">Resolution/status/ownership consistency checks</div>
        </div>
        {data && (
          <span className={`chip ${data.total_anomaly_count > 0 ? "warning" : "good"}`}>
            <span className="dot" />
            {formatNumber(data.total_anomaly_count)}
          </span>
        )}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 120, width: "100%" }} />
      ) : groups.length === 0 ? (
        <div className="card-sub">None found in this period ✓</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {groups.map(([key, group]) => (
            <div key={key}>
              <button
                className="table-toggle"
                style={{
                  display: "flex",
                  width: "100%",
                  justifyContent: "space-between",
                  padding: "6px 0",
                }}
                onClick={() => setExpanded(expanded === key ? null : key)}
              >
                <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>{group.label}</span>
                <span>
                  {group.count}
                  {group.truncated ? "+" : ""}
                </span>
              </button>
              {expanded === key && (
                <div className="tbl-wrap" style={{ marginBottom: 8 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Ticket</th>
                        <th>Status</th>
                        <th>Module</th>
                        <th>Final resolution</th>
                        <th>Owner</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.tickets.map((t) => (
                        <tr key={t.ticket_id}>
                          <td className="name-cell" title={t.subject}>
                            {t.subject || t.ticket_id}
                          </td>
                          <td>{t.canonical_status}</td>
                          <td>{t.module}</td>
                          <td>{t.final_resolution ?? "—"}</td>
                          <td>{t.owner_name ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
