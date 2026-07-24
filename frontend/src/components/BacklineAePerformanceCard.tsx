import type { BacklineAePerformance } from "../types";
import { formatHours, formatNumber } from "../format";

interface Props {
  data: BacklineAePerformance | null;
  loading: boolean;
}

// The two entry paths into backline, per hubspot_pipeline/stage_timing.py.
const BUG_BOUNTY_PATH = "Bug Bounty";
const FRONTLINE_ESCALATION_PATH = "Frontline Escalation";

export function BacklineAePerformanceCard({ data, loading }: Props) {
  const rows = data?.ae_performance ?? [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Backline AE performance</div>
          <div className="card-sub">By whoever holds Backline Engineer, this period</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No backline-assigned tickets in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>AE</th>
                <th className="num">Assigned this period</th>
                <th className="num">Resolved this period</th>
                <th className="num">Median AE time</th>
                <th className="num">Median ticket TTR</th>
                <th className="num">Bug Bounty avg</th>
                <th className="num">Frontline Esc. avg</th>
                <th className="num">Escalated to Eng</th>
                <th className="num">High priority</th>
                <th className="num">All resolved</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((ae) => (
                <tr key={ae.backline_engineer}>
                  <td className="name-cell">{ae.backline_engineer}</td>
                  <td className="num">{formatNumber(ae.tickets_handled_count)}</td>
                  <td className="num">{formatNumber(ae.tickets_resolved_count)}</td>
                  <td className="num">{formatHours(ae.ae_stage_time_hours.median)}</td>
                  <td className="num">{formatHours(ae.ticket_resolution_time_hours.median)}</td>
                  <td className="num">
                    {formatHours(ae.ae_stage_time_hours_by_path[BUG_BOUNTY_PATH]?.average ?? null)}
                  </td>
                  <td className="num">
                    {formatHours(
                      ae.ae_stage_time_hours_by_path[FRONTLINE_ESCALATION_PATH]?.average ?? null
                    )}
                  </td>
                  <td className="num">{formatNumber(ae.escalated_to_engineering_count)}</td>
                  <td className="num">{formatNumber(ae.high_priority_ticket_count)}</td>
                  <td className="num">
                    {ae.all_resolved ? (
                      <span className="chip good">Yes</span>
                    ) : (
                      <span className="chip warning">No</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
