import { useState } from "react";
import type { SlackIssues } from "../types";
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

/** A ticket's derived_priority is always one of PRIORITY_ORDER (see
 * hubspot_pipeline/priority.py) -- "Other" only exists as a defensive
 * pie/bar slice for values that don't fit that set, so it's matched by
 * exclusion rather than by a real priority string. */
function matchesBucket(bucket: string, priority: string): boolean {
  return bucket === "Other" ? !PRIORITY_ORDER.includes(priority) : priority === bucket;
}

/** Distribution of Slack-reported issues by derived priority -- clicking a
 * bar or a pie slice drills into that priority's individual tickets, same
 * click-to-reveal pattern as NpsCard. */
export function SlackPriorityCard({ data, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const counts = data?.issue_count_by_priority ?? {};
  const total = Object.values(counts).reduce((sum, c) => sum + c, 0);
  const items = PRIORITY_ORDER.filter((p) => counts[p]).map((p, i) => ({
    label: p,
    value: counts[p],
    color: ORDINAL_RAMP[i],
  }));

  const toggle = (bucket: string) => setExpanded(expanded === bucket ? null : bucket);
  const drilldownIssues = expanded ? (data?.issues ?? []).filter((i) => matchesBucket(expanded, i.priority)) : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Issues by priority</div>
          <div className="card-sub">
            Derived priority of Slack-reported issues
            {total > 0 && ` · ${total} issue${total === 1 ? "" : "s"} total`}
          </div>
        </div>
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
                  {expanded} &middot; {drilldownIssues.length} issue
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
