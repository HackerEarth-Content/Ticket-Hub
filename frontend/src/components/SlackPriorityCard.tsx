import { useState } from "react";
import type { SlackIssue, SlackIssues } from "../types";
import { BarList } from "./BarList";
import { IssueTable } from "./ContentOnCallTable";
import { SlackPriorityPieChart } from "./SlackPriorityPieChart";

interface Props {
  data: SlackIssues | null;
  loading: boolean;
}

// Same severity order/ramp as SlackPriorityPieChart -- kept in sync here so
// the BarList rows and the pie slices agree on color.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const ORDINAL_RAMP = ["var(--ord-1)", "var(--ord-2)", "var(--ord-4)", "var(--ord-5)"];

// Support's P-level equivalent for each derived priority, shown alongside
// the bucket name since that's the scale the team actually pages on.
const P_LABEL: Record<string, string> = {
  LOW: "P3/P4",
  MEDIUM: "P2",
  HIGH: "P1",
  URGENT: "P0",
};

/** A ticket's derived_priority is always one of PRIORITY_ORDER (see
 * hubspot_pipeline/priority.py) -- "Other" only exists as a defensive
 * pie/bar slice for values that don't fit that set, so it's matched by
 * exclusion rather than by a real priority string. */
function matchesBucket(bucket: string, priority: string): boolean {
  return bucket === "Other" ? !PRIORITY_ORDER.includes(priority) : priority === bucket;
}

const TEAM_LABELS: Record<string, string> = {
  content: "Content",
  engg_oncall: "Engg Oncall",
  uncategorized: "Uncategorized",
};

/** Distribution of Slack-reported issues by derived priority -- clicking a
 * bar or a pie slice drills into that priority's individual tickets, same
 * click-to-reveal pattern as NpsCard. The dropdown narrows the histogram to
 * one team or one channel; counts come from the server-side slices
 * (priority_by_team / priority_by_channel) so they stay correct past the
 * drilldown cap. One filter at a time -- team and channel overlap anyway. */
export function SlackPriorityCard({ data, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState("all"); // "all" | "team:<key>" | "channel:<name>"

  const filterKey = filter.slice(filter.indexOf(":") + 1);
  const counts =
    (filter === "all"
      ? data?.issue_count_by_priority
      : filter.startsWith("team:")
        ? data?.priority_by_team?.[filterKey]
        : data?.priority_by_channel?.[filterKey]) ?? {};
  const channels = Object.entries(data?.issue_count_by_channel ?? {}).sort((a, b) => b[1] - a[1]);
  const total = Object.values(counts).reduce((sum, c) => sum + c, 0);
  const items = PRIORITY_ORDER.filter((p) => counts[p]).map((p, i) => ({
    label: p,
    displayLabel: P_LABEL[p] ? `${p} (${P_LABEL[p]})` : p,
    value: counts[p],
    color: ORDINAL_RAMP[i],
  }));

  const toggle = (bucket: string) => setExpanded(expanded === bucket ? null : bucket);
  const matchesFilter = (i: SlackIssue) =>
    filter === "all" ||
    (filter.startsWith("team:") ? i.team === filterKey : i.channel === filterKey);
  const drilldownIssues = expanded
    ? (data?.issues ?? []).filter((i) => matchesBucket(expanded, i.priority) && matchesFilter(i))
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Issues by priority</div>
          <div className="card-sub">
            Derived priority of Slack-reported issues
            {filter !== "all" && ` · ${filter.startsWith("team:") ? TEAM_LABELS[filterKey] ?? filterKey : `#${filterKey}`}`}
            {total > 0 && ` · ${total} issue${total === 1 ? "" : "s"} total`}
          </div>
        </div>
        <select
          className="select"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setExpanded(null);
          }}
          disabled={loading}
        >
          <option value="all">All issues</option>
          <optgroup label="Team">
            {Object.entries(TEAM_LABELS).map(([key, label]) => (
              <option key={key} value={`team:${key}`}>
                {label}
              </option>
            ))}
          </optgroup>
          <optgroup label="Channel">
            {channels.map(([name]) => (
              <option key={name} value={`channel:${name}`}>
                {name === "Unknown" ? "Unknown channel" : `#${name}`}
              </option>
            ))}
          </optgroup>
        </select>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : total === 0 ? (
        <div className="card-sub">No Slack-reported issues in this period.</div>
      ) : (
        <>
          <div className="chart-columns">
            <div className="chart-col-list">
              <BarList items={items} activeLabel={expanded} onItemClick={toggle} />
            </div>
            <div className="chart-col-chart">
              <SlackPriorityPieChart
                data={counts}
                activePriority={expanded}
                onSliceClick={toggle}
                loading={false}
              />
            </div>
          </div>
          {expanded && (
            <div className="chart-drilldown">
              <div className="chart-drilldown-head">
                <div className="card-sub">
                  {P_LABEL[expanded] ? `${expanded} (${P_LABEL[expanded]})` : expanded} &middot;{" "}
                  {drilldownIssues.length} issue
                  {drilldownIssues.length === 1 ? "" : "s"}
                </div>
                <button type="button" className="chart-drilldown-close" onClick={() => setExpanded(null)}>
                  Close ✕
                </button>
              </div>
              {drilldownIssues.length === 0 ? (
                <div className="card-sub">No {expanded} issues in this period.</div>
              ) : (
                <IssueTable rows={drilldownIssues} />
              )}
              {data?.truncated && (
                <div className="card-sub" style={{ marginTop: 8 }}>
                  Only the first {data.issues.length} of {data.issue_count} issues this period are
                  available to drill into.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
