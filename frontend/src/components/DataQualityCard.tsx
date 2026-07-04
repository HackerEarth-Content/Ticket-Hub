import type { DataQuality } from "../types";
import { formatPercent } from "../format";
import { StatTile, StatTileSkeleton } from "./StatTile";

interface Props {
  dataQuality: DataQuality | null;
  loading: boolean;
}

export function DataQualityCard({ dataQuality, loading }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">Data quality</div>
      </div>
      <div className="stat-strip" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {loading || !dataQuality ? (
          <>
            <StatTileSkeleton />
            <StatTileSkeleton />
          </>
        ) : (
          <>
            <StatTile
              label="Priority inferred"
              value={formatPercent(dataQuality.priority_inferred_percentage)}
              foot="real field mostly blank"
            />
            <StatTile
              label="Uncategorized"
              value={formatPercent(dataQuality.uncategorized_ticket_percentage)}
            />
          </>
        )}
      </div>
    </div>
  );
}
