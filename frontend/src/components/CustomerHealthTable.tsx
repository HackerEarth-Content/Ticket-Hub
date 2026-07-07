import type { CustomerDetailsEntry, CustomerDetails } from "../types";
import { formatHours, formatNumber, formatPercent } from "../format";

interface Props {
  data: CustomerDetails | null;
  loading: boolean;
}

function slaCompliancePercentage(c: CustomerDetailsEntry): number | null {
  const evaluated = c.sla_met_count + c.sla_breached_count;
  return evaluated ? (100 * c.sla_met_count) / evaluated : null;
}

/** The remaining per-account signals that don't need a chart -- SLA
 * compliance, how fast (first response + resolution), how often escalated,
 * and current backlog. One row per account so they're all comparable at a
 * glance, instead of five separate single-metric cards. */
export function CustomerHealthTable({ data, loading }: Props) {
  const customers = data?.customers ?? [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Account health</div>
          <div className="card-sub">
            SLA compliance, speed, escalation rate, and current open backlog per top account
          </div>
        </div>
      </div>
      {loading || !data ? (
        <div className="skeleton" style={{ height: 220, width: "100%" }} />
      ) : customers.length === 0 ? (
        <div className="card-sub">No identified customer accounts in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th className="num">SLA compliance</th>
                <th className="num">Median first response</th>
                <th className="num">Median resolution</th>
                <th className="num">Escalated</th>
                <th className="num">Open backlog</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => {
                const slaPct = slaCompliancePercentage(c);
                return (
                  <tr key={c.customer_name}>
                    <td className="name-cell" title={c.customer_name}>
                      {c.customer_name}
                    </td>
                    <td className="num">
                      <span
                        style={
                          slaPct !== null && slaPct < 80 ? { color: "var(--status-critical)" } : undefined
                        }
                      >
                        {formatPercent(slaPct)}
                      </span>
                    </td>
                    <td className="num">{formatHours(c.median_first_response_hours)}</td>
                    <td className="num">{formatHours(c.median_resolution_time_hours)}</td>
                    <td className="num">
                      {formatNumber(c.escalated_count)}
                      {c.escalated_percentage !== null && (
                        <span className="card-sub"> ({formatPercent(c.escalated_percentage)})</span>
                      )}
                    </td>
                    <td className="num">
                      <span
                        style={c.open_backlog_count > 0 ? { color: "var(--status-warning)" } : undefined}
                      >
                        {formatNumber(c.open_backlog_count)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
