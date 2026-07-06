import type { BacklineEscalations } from "../types";
import { formatHours } from "../format";

interface Props {
  data: BacklineEscalations | null;
  loading: boolean;
}

function liveWaitChip(hours: number | null) {
  if (hours === null) return <span className="num">—</span>;
  const tone = hours > 48 ? "critical" : hours > 24 ? "serious" : "warning";
  return (
    <span className="num">
      <span className={`chip ${tone}`}>{formatHours(hours)}</span>
    </span>
  );
}

export function EscalationsTable({ data, loading }: Props) {
  const rows = data?.escalations ?? [];

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div>
          <div className="card-title">Escalations past backline</div>
          <div className="card-sub">
            Tickets that reached QA/Platform or Engineering
            {data ? ` · ${data.escalation_count} this period` : ""}
            {data?.truncated ? " (showing first 100)" : ""}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No escalations in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Owner</th>
                <th>Backline AE</th>
                <th>Escalation path</th>
                <th>Status</th>
                <th className="num">Live wait</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.ticket_id}>
                  <td className="name-cell" title={e.subject}>
                    {e.subject || e.ticket_id}
                  </td>
                  <td>{e.owner_name ?? "—"}</td>
                  <td>{e.backline_engineer ?? "—"}</td>
                  <td className="pipeline-tag">{e.escalation_path}</td>
                  <td>{e.canonical_status}</td>
                  <td>{liveWaitChip(e.live_wait_time_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
