import type { CustomerVolume } from "../types";
import { formatNumber, formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  data: CustomerVolume | null;
  loading: boolean;
}

/** Headline numbers for the Customers tab -- identification coverage is the
 * fact that actually needs explaining here (most tickets have no account
 * attached at all), so it leads, not the chart. */
export function CustomerOverviewCard({ data, loading }: Props) {
  const topCustomer = data?.top_customers[0] ?? null;
  const coveragePct = data && data.total_ticket_count
    ? (data.identified_ticket_count / data.total_ticket_count) * 100
    : null;
  const noAccountPct = data && data.total_ticket_count
    ? (data.no_account_ticket_count / data.total_ticket_count) * 100
    : null;

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div>
          <div className="card-title">Customers at a glance</div>
          <div className="card-sub">
            Account name comes from HubSpot's blackops_account_name / hs_primary_company_name
            ticket properties -- most tickets here are individual candidates with no account,
            not a data gap
          </div>
        </div>
        {topCustomer && (
          <span className="chip neutral" title="Highest-volume identified account this period">
            Top: {topCustomer.customer_name} ({formatNumber(topCustomer.ticket_count)})
          </span>
        )}
      </div>
      <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        {loading || !data ? (
          Array.from({ length: 4 }).map((_, i) => <StatTileSkeleton key={i} />)
        ) : (
          <>
            <StatTile label="Total tickets" value={formatNumber(data.total_ticket_count)} />
            <StatTile
              label="Identified accounts"
              value={formatNumber(data.identified_customer_count)}
              foot={`${formatNumber(data.identified_ticket_count)} tickets`}
            />
            <StatTile
              label="Customer Tickets"
              value={formatPercent(coveragePct)}
              tone={coveragePct !== null && coveragePct < 10 ? "warn" : "default"}
              foot="of all tickets"
            />
            <StatTile
              label="Candidate Tickets"
              value={formatPercent(noAccountPct)}
              foot={`${formatNumber(data.no_account_ticket_count)} tickets — individual candidates, mostly`}
            />
          </>
        )}
      </div>
    </div>
  );
}
