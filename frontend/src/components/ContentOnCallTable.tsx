import { useState } from "react";
import type { SlackIssue, SlackIssues, SlackWorkflowTicketGroup } from "../types";
import { hubspotTicketUrl } from "../format";

interface Props {
  data: SlackIssues | null;
  loading: boolean;
}

export function IssueTable({ rows }: { rows: SlackIssue[] }) {
  return (
    <div className="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Reported by</th>
            <th>Assigned to</th>
            <th>Priority</th>
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
              <td>{issue.priority}</td>
              <td>{issue.stage_label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type WorkflowCategory = "content" | "engg_oncall";

const CATEGORY_LABELS: Record<WorkflowCategory, string> = {
  content: "Content requests",
  engg_oncall: "Engg Oncall",
};

export function ContentOnCallTable({ data, loading }: Props) {
  const [category, setCategory] = useState<WorkflowCategory>("content");

  const byCategory = data?.tickets_by_workflow_category;
  const group: SlackWorkflowTicketGroup | undefined = byCategory?.[category];
  const rows = group?.tickets ?? [];
  const uncategorized = byCategory?.uncategorized;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Slack-reported issues</div>
          <div className="card-sub">
            Tickets reported through the Slack source
            {group ? ` · ${group.count} this period` : ""}
            {group?.truncated ? " (showing first 100)" : ""}
          </div>
        </div>
        <select
          className="select"
          value={category}
          onChange={(e) => setCategory(e.target.value as WorkflowCategory)}
          disabled={loading}
        >
          {(Object.keys(CATEGORY_LABELS) as WorkflowCategory[]).map((key) => (
            <option key={key} value={key}>
              {CATEGORY_LABELS[key]}
            </option>
          ))}
        </select>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No {CATEGORY_LABELS[category].toLowerCase()} in this period.</div>
      ) : (
        <IssueTable rows={rows} />
      )}

      {!loading && uncategorized && uncategorized.count > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary className="card-sub" style={{ cursor: "pointer" }}>
            Uncategorized — no workflow tag ({uncategorized.count})
          </summary>
          <div style={{ marginTop: 10 }}>
            <IssueTable rows={uncategorized.tickets} />
          </div>
        </details>
      )}
    </div>
  );
}
