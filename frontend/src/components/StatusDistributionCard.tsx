import type { StatusDistribution } from "../types";
import { BarList } from "./BarList";
import { formatNumber } from "../format";

// Lifecycle order -- swapping it would change the meaning, so this is an
// ordinal ramp (single hue, monotone lightness), not a categorical rainbow.
const LIFECYCLE_ORDER = ["New", "Open", "Pending", "Closing"];
const ORDINAL_RAMP = ["var(--ord-1)", "var(--ord-2)", "var(--ord-3)", "var(--ord-4)"];

interface Props {
  distribution: StatusDistribution | null;
  loading: boolean;
}

export function StatusDistributionCard({ distribution, loading }: Props) {
  const counts = distribution?.ticket_count_by_status ?? {};
  const resolved = counts["Resolved"] ?? 0;
  const activeTotal = LIFECYCLE_ORDER.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
  const grandTotal = activeTotal + resolved;

  const items = LIFECYCLE_ORDER.map((stage, i) => ({
    label: stage,
    value: counts[stage] ?? 0,
    color: ORDINAL_RAMP[i],
  }));

  return (
    <div className="grid cols-2" style={{ marginBottom: 14 }}>
      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Active pipeline, by stage</div>
            <div className="card-sub">Excludes resolved — shown separately, right</div>
          </div>
        </div>
        {loading ? (
          <div className="skeleton" style={{ height: 120, width: "100%" }} />
        ) : (
          <>
            <BarList items={items} />
            <div className="card-sub" style={{ marginTop: 12 }}>
              Ordered by lifecycle stage — color deepens toward resolution, not by volume.
            </div>
          </>
        )}
      </div>
      <div
        className="card"
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
        }}
      >
        <div className="card-sub" style={{ marginBottom: 6 }}>
          Resolved this period
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 650,
            letterSpacing: "-0.02em",
            color: "var(--status-good)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {loading ? "—" : formatNumber(resolved)}
        </div>
        {!loading && grandTotal > 0 && (
          <div className="card-sub" style={{ marginTop: 6 }}>
            {((100 * resolved) / grandTotal).toFixed(1)}% of all active + resolved tickets this
            period
          </div>
        )}
      </div>
    </div>
  );
}
