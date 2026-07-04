import type { LiveToday } from "../types";
import { StatTile, StatTileSkeleton } from "./StatTile";

const ACTIVE_STAGES = ["New", "Open", "Pending", "Closing"];

interface Props {
  live: LiveToday | null;
  loading: boolean;
}

export function LiveStatusStrip({ live, loading }: Props) {
  if (loading || !live) {
    return (
      <div className="stat-strip" style={{ marginBottom: 14 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <StatTileSkeleton key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="stat-strip" style={{ marginBottom: 14 }}>
      {ACTIVE_STAGES.map((stage) => (
        <StatTile
          key={stage}
          label={stage}
          value={live.open_ticket_count_by_status[stage] ?? 0}
        />
      ))}
      <StatTile label="Resolved today" value={live.resolved_today_count} tone="good" />
      <StatTile
        label="SLA breaching soon"
        value={live.sla_breaching_soon_count}
        tone={live.sla_breaching_soon_count > 0 ? "warn" : "default"}
        foot={live.sla_breaching_soon_count > 0 ? "needs attention" : undefined}
      />
    </div>
  );
}
