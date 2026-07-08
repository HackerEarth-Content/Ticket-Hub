import type { LiveToday } from "../types";
import { formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

// (status key, tile label) -- only "Pending" gets a different display label.
const ACTIVE_STAGES: [string, string][] = [
  ["New", "New"],
  ["Open", "Open"],
  ["Pending", "Pending on teams"],
];

interface Props {
  live: LiveToday | null;
  loading: boolean;
}

export function LiveStatusStrip({ live, loading }: Props) {
  if (loading || !live) {
    return (
      <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 14 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <StatTileSkeleton key={i} />
        ))}
      </div>
    );
  }

  const frtOnTimePct = live.first_response_on_time_today_percentage;

  return (
    <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 14 }}>
      {ACTIVE_STAGES.map(([status, label]) => (
        <StatTile
          key={status}
          label={label}
          value={live.open_ticket_count_by_status[status] ?? 0}
        />
      ))}
      <StatTile
        label="FRT on time"
        value={live.first_response_on_time_today_count}
        tone={frtOnTimePct === null ? "default" : frtOnTimePct >= 80 ? "good" : "warn"}
        foot={frtOnTimePct !== null ? `${formatPercent(frtOnTimePct)} of today's replies` : undefined}
      />
    </div>
  );
}
