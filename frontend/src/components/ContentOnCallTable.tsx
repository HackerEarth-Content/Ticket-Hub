import type { SlackIssues } from "../types";
import { hubspotTicketUrl } from "../format";

interface Props {
  data: SlackIssues | null;
  loading: boolean;
}

export function ContentOnCallTable({ data, loading }: Props) {
  const rows = data?.issues ?? [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Slack-reported issues</div>
          <div className="card-sub">
            Tickets reported through the Slack source
            {data ? ` · ${data.issue_count} this period` : ""}
            {data?.truncated ? " (showing first 100)" : ""}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No Slack-reported issues in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Reported by</th>
                <th>Assigned to</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((issue) => (
                <tr key={issue.ticket_id}>
                  <td className="name-cell" title={issue.subject}>
                    <a href={hubspotTicketUrl(issue.ticket_id)} target="_blank" rel="noopener noreferrer">
                      {issue.subject || issue.ticket_id}
                    </a>
                    <div className="card-sub">#{issue.ticket_id}</div>
                  </td>
                  <td>
                    {issue.reporter_name}
                    {issue.reporter_is_fallback_owner && (
                      <div className="card-sub">not found in description, showing assignee</div>
                    )}
                  </td>
                  <td>{issue.owner_name ?? "—"}</td>
                  <td>{issue.stage_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
