import type { AgentKpi } from "../types";
import { formatHours, formatNumber } from "../format";

interface Props {
  agents: AgentKpi[];
  loading: boolean;
}

export function AgentLeaderboard({ agents, loading }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">Agent leaderboard</div>
        <div className="card-sub">By ticket volume, this period</div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 160, width: "100%" }} />
      ) : agents.length === 0 ? (
        <div className="card-sub">No assigned tickets in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th className="num">Tickets</th>
                <th className="num">Median resolution</th>
              </tr>
            </thead>
            <tbody>
              {agents.slice(0, 8).map((a) => (
                <tr key={a.owner_id}>
                  <td className="name-cell">{a.owner_name ?? `Owner ${a.owner_id}`}</td>
                  <td className="num">{formatNumber(a.ticket_count)}</td>
                  <td className="num">{formatHours(a.median_resolution_time_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
