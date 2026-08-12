import type { FrontlineFcr, FrontlineFrt } from "../types";
import { formatNumber, formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  frt: FrontlineFrt | null;
  fcr: FrontlineFcr | null;
  loading: boolean;
}

/** FRT + FCR together -- both are "how good was the frontline touch",
 * unlike SlaPanel which covers HubSpot's own close/response SLA clocks. */
export function FrontlineQualityCard({ frt, fcr, loading }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Frontline quality</div>
          <div className="card-sub">
            First response {frt ? `(${frt.sla_threshold_minutes}m SLA)` : ""} & first contact resolution
          </div>
        </div>
      </div>
      <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        {loading || !frt || !fcr ? (
          <>
            <StatTileSkeleton />
            <StatTileSkeleton />
            <StatTileSkeleton />
            <StatTileSkeleton />
          </>
        ) : (
          <>
            <StatTile
              label="FRT on-time"
              value={formatPercent(frt.on_time_percentage)}
              tone={(frt.on_time_percentage ?? 100) < 80 ? "warn" : "good"}
              foot={`${formatNumber(frt.missed_count)} missed`}
            />
            <StatTile
              label="Awaiting response from user"
              value={formatNumber(frt.awaiting_reply_overdue_count)}
            />
            <StatTile
              label="First contact resolution"
              value={formatPercent(fcr.first_contact_resolution_percentage)}
              foot={`${formatNumber(fcr.fcr_true_count)} of ${formatNumber(
                fcr.fcr_true_count + fcr.fcr_false_count
              )}`}
            />
            <StatTile
              label="FCR resolved <24h"
              value={formatPercent(fcr.fcr_resolved_within_24_hours_percentage)}
            />
          </>
        )}
      </div>
    </div>
  );
}
