import { useMemo, useState } from "react";
import type { SlackIssue, SlackIssues, SlackWorkflowTicketGroup } from "../types";
import { hubspotTicketUrl } from "../format";

interface Props {
  data: SlackIssues | null;
  loading: boolean;
}

// Priority → existing chip severity classes (App.css) -- unknown values fall
// back to neutral, same defensive stance as SlackPriorityCard's "Other".
const PRIORITY_CHIP: Record<string, string> = {
  LOW: "good",
  MEDIUM: "warning",
  HIGH: "serious",
  URGENT: "critical",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
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
            <th>Created</th>
            <th>Resolved/Closed</th>
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
              <td>
                <span className={`chip ${PRIORITY_CHIP[issue.priority] ?? "neutral"}`}>
                  {issue.priority}
                </span>
              </td>
              <td>{issue.stage_label}</td>
              <td>{formatDate(issue.created_at)}</td>
              <td>{formatDate(issue.closed_at)}</td>
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

type StatusSort = "default" | "stage_label";

const STATUS_SORT_LABELS: Record<StatusSort, string> = {
  default: "Sort: Newest",
  stage_label: "Sort: Status",
};

// Severity order, not alphabetical -- same ramp as SlackPriorityCard/SlackPriorityPieChart.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const ALL = "all";

/** Sortable, filterable, paginated view over an already-fetched issue list.
 * Filtering/sorting/paging all happen client-side -- the server already
 * returns the full (capped at 100) list for the period, so there's nothing
 * to round-trip. */
function IssueListing({ rows }: { rows: SlackIssue[] }) {
  const [reporterFilter, setReporterFilter] = useState(ALL);
  const [ownerFilter, setOwnerFilter] = useState(ALL);
  const [priorityFilter, setPriorityFilter] = useState(ALL);
  const [sortBy, setSortBy] = useState<StatusSort>("default");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [perPage, setPerPage] = useState(10);
  const [page, setPage] = useState(1);

  const reporterOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.reporter_name))).sort(),
    [rows],
  );
  const ownerOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.owner_name ?? "Unassigned"))).sort(),
    [rows],
  );
  const priorityOptions = useMemo(() => {
    const present = new Set(rows.map((r) => r.priority));
    const known = PRIORITY_ORDER.filter((p) => present.has(p));
    const other = Array.from(present).filter((p) => !PRIORITY_ORDER.includes(p)).sort();
    return [...known, ...other];
  }, [rows]);

  const filtered = useMemo(
    () =>
      rows.filter(
        (r) =>
          (reporterFilter === ALL || r.reporter_name === reporterFilter) &&
          (ownerFilter === ALL || (r.owner_name ?? "Unassigned") === ownerFilter) &&
          (priorityFilter === ALL || r.priority === priorityFilter),
      ),
    [rows, reporterFilter, ownerFilter, priorityFilter],
  );

  const sorted = useMemo(() => {
    if (sortBy === "default") return filtered;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => dir * a.stage_label.localeCompare(b.stage_label));
  }, [filtered, sortBy, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const pageRows = sorted.slice((currentPage - 1) * perPage, currentPage * perPage);

  return (
    <div>
      <div className="card-sub" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
        <select
          className="select"
          value={reporterFilter}
          onChange={(e) => {
            setReporterFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value={ALL}>All reporters</option>
          {reporterOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={ownerFilter}
          onChange={(e) => {
            setOwnerFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value={ALL}>All assignees</option>
          {ownerOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={priorityFilter}
          onChange={(e) => {
            setPriorityFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value={ALL}>All priorities</option>
          {priorityOptions.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select
          className="select"
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value as StatusSort);
            setPage(1);
          }}
        >
          {(Object.keys(STATUS_SORT_LABELS) as StatusSort[]).map((key) => (
            <option key={key} value={key}>
              {STATUS_SORT_LABELS[key]}
            </option>
          ))}
        </select>
        {sortBy !== "default" && (
          <button
            type="button"
            className="chart-drilldown-close"
            onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
          >
            {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
          </button>
        )}
        <select
          className="select"
          value={perPage}
          onChange={(e) => {
            setPerPage(Number(e.target.value));
            setPage(1);
          }}
        >
          {PAGE_SIZE_OPTIONS.map((n) => (
            <option key={n} value={n}>
              {n} / page
            </option>
          ))}
        </select>
      </div>
      {pageRows.length === 0 ? (
        <div className="card-sub">No tickets match the current filters.</div>
      ) : (
        <IssueTable rows={pageRows} />
      )}
      <div
        className="card-sub"
        style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", marginTop: 8 }}
      >
        <span>
          Page {currentPage} of {totalPages} · {sorted.length} ticket{sorted.length === 1 ? "" : "s"}
        </span>
        <span style={{ display: "flex", gap: 6 }}>
          <button type="button" className="chart-drilldown-close" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
            ← Prev
          </button>
          <button
            type="button"
            className="chart-drilldown-close"
            disabled={currentPage >= totalPages}
            onClick={() => setPage(currentPage + 1)}
          >
            Next →
          </button>
        </span>
      </div>
    </div>
  );
}

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
        <IssueListing rows={rows} />
      )}

      {!loading && uncategorized && uncategorized.count > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary className="card-sub" style={{ cursor: "pointer" }}>
            Uncategorized — no workflow tag ({uncategorized.count})
          </summary>
          <div style={{ marginTop: 10 }}>
            <IssueListing rows={uncategorized.tickets} />
          </div>
        </details>
      )}
    </div>
  );
}
