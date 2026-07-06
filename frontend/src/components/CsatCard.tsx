import type { Csat } from "../types";
import { formatPercent } from "../format";
import { BarList } from "./BarList";

interface Props {
  csat: Csat | null;
  loading: boolean;
}

export function CsatCard({ csat, loading }: Props) {
  const items = csat
    ? Object.entries(csat.response_count_by_rating)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([rating, count]) => ({
          label: `Rating ${rating}`,
          value: count,
          color: "var(--ink-3)",
        }))
    : [];

  const channelItems = csat
    ? Object.entries(csat.response_count_by_rating_and_channel)
        .map(([channel, byRating]) => ({
          label: channel,
          value: Object.values(byRating).reduce((sum, n) => sum + n, 0),
          color: "var(--accent-blue)",
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  const channelNormalizedItems = csat
    ? Object.entries(csat.normalized_csat_percentage_by_channel)
        .filter((entry): entry is [string, number] => entry[1] !== null)
        .map(([channel, pct]) => ({
          label: channel,
          value: pct,
          displayValue: formatPercent(pct),
          color: "var(--accent-blue)",
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">CSAT responses</div>
          {csat && csat.normalized_csat_percentage !== null && (
            <div className="card-sub">
              Normalized CSAT: {formatPercent(csat.normalized_csat_percentage)}
            </div>
          )}
        </div>
        {!csat || !csat.rating_scale_confirmed ? (
          <span className="chip neutral">
            <span className="dot" />
            scale unconfirmed
          </span>
        ) : null}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">No CSAT responses in this period.</div>
      ) : (
        <>
          <BarList items={items} />
          {channelItems.length > 0 && (
            <>
              <div className="card-sub" style={{ margin: "14px 0 8px" }}>
                By channel
              </div>
              <BarList items={channelItems} />
            </>
          )}
          {channelNormalizedItems.length > 0 && (
            <>
              <div className="card-sub" style={{ margin: "14px 0 8px" }}>
                Normalized CSAT % by channel
              </div>
              <BarList items={channelNormalizedItems} maxValue={100} />
            </>
          )}
        </>
      )}
    </div>
  );
}
