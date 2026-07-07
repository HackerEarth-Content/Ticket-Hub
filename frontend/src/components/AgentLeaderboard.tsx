import type { AgentKpi } from "../types";
import { formatHours, formatNumber, formatPercent } from "../format";

interface Props {
  agents: AgentKpi[];
  loading: boolean;
}

function AgentRowCells({ a }: { a: AgentKpi }) {
  return (
    <>
      <td className="name-cell">
        {a.owner_id === "unassigned" ? (
          <span className="chip neutral">Unassigned</span>
        ) : (
          a.owner_name ?? `Owner ${a.owner_id}`
        )}
      </td>
      <td className="num">{formatNumber(a.ticket_count)}</td>
      <td className="num">{formatNumber(a.non_actionable_count)}</td>
      <td className="num">{formatNumber(a.closed_count)}</td>
      <td className="num">{formatNumber(a.still_open_count)}</td>
      <td className="num">{formatHours(a.median_resolution_time_hours)}</td>
      <td className="num">{formatHours(a.mean_resolution_time_hours)}</td>
      <td className="num">{formatPercent(a.first_response_sla_on_time_percentage)}</td>
      <td className="num">{formatPercent(a.first_contact_resolution_percentage)}</td>
      <td className="num">{formatPercent(a.backline_escalation_percentage)}</td>
      <td className="num">{formatNumber(a.resolved_by_backline_engineering_count)}</td>
      <td className="num">{formatNumber(a.escalated_to_engineering_count)}</td>
      <td className="num">
        {formatPercent(a.csat_normalized_percentage)}
        {a.csat_response_count > 0 && (
          <span className="card-sub" style={{ marginLeft: 4 }}>
            ({a.csat_response_count})
          </span>
        )}
      </td>
    </>
  );
}

export function AgentLeaderboard({ agents, loading }: Props) {
  // "team_total" is a synthetic aggregate row, computed independently of the
  // per-owner rows (see get_agent_kpis) -- kept out of the ranked list and
  // pinned as a footer instead, so it doesn't crowd out a real top-8 agent.
  const rows = agents.filter((a) => a.owner_id !== "team_total");
  const teamTotal = agents.find((a) => a.owner_id === "team_total") ?? null;

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">Agent leaderboard</div>
        <div className="card-sub">By ticket volume, this period</div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 160, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No assigned tickets in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th className="num">Tickets</th>
                <th className="num">Non-actionable</th>
                <th className="num">Closed</th>
                <th className="num">Still open</th>
                <th className="num">Median resolution</th>
                <th className="num">Mean resolution</th>
                <th className="num">FRT on-time</th>
                <th className="num">FCR</th>
                <th className="num">Escalated</th>
                <th className="num">Resolved by Backline Eng</th>
                <th className="num">Escalated to Eng</th>
                <th className="num">CSAT</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 8).map((a) => (
                <tr key={a.owner_id}>
                  <AgentRowCells a={a} />
                </tr>
              ))}
            </tbody>
            {teamTotal && (
              <tfoot>
                <tr className="tbl-total-row">
                  <AgentRowCells a={teamTotal} />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  );
}
