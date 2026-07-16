import { useState } from "react";
import type { Nps, NpsBucket } from "../types";
import { BarList } from "./BarList";
import { NpsDistributionPieChart } from "./NpsDistributionPieChart";

interface Props {
  nps: Nps | null;
  loading: boolean;
  topCustomerNames: string[];
  onNavigateToCustomer: (name: string) => void;
}

const BUCKET_LABELS: Record<NpsBucket, string> = {
  promoter: "Promoters",
  passive: "Passives",
  detractor: "Detractors",
};

export function NpsCard({ nps, loading, topCustomerNames, onNavigateToCustomer }: Props) {
  const [expanded, setExpanded] = useState<NpsBucket | null>(null);

  const items = nps
    ? (Object.keys(BUCKET_LABELS) as NpsBucket[]).map((bucket) => ({
        label: BUCKET_LABELS[bucket],
        value: nps[`${bucket}_count` as const],
        color: "var(--ink-3)",
      }))
    : [];

  const toggle = (bucket: NpsBucket) => setExpanded(expanded === bucket ? null : bucket);
  const responses = expanded ? nps?.responses_by_bucket[expanded] ?? [] : [];

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">NPS responses</div>
          {nps && nps.nps_score !== null && (
            <div className="card-sub">NPS score: {nps.nps_score}</div>
          )}
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : !nps || nps.total_response_count === 0 ? (
        <div className="card-sub">No NPS responses in this period.</div>
      ) : (
        <>
          <div className="chart-columns">
            <div className="chart-col-list">
              <BarList
                items={items}
                activeLabel={expanded ? BUCKET_LABELS[expanded] : null}
                onItemClick={(label) => {
                  const bucket = (Object.keys(BUCKET_LABELS) as NpsBucket[]).find(
                    (b) => BUCKET_LABELS[b] === label
                  );
                  if (bucket) toggle(bucket);
                }}
              />
            </div>
            <div className="chart-col-chart">
              <NpsDistributionPieChart
                promoterCount={nps.promoter_count}
                passiveCount={nps.passive_count}
                detractorCount={nps.detractor_count}
                activeBucket={expanded}
                onSliceClick={toggle}
                loading={false}
              />
            </div>
          </div>
          {expanded && (
            <div className="chart-drilldown">
              <div className="chart-drilldown-head">
                <div className="card-sub">
                  {BUCKET_LABELS[expanded]} &middot; {responses.length} response
                  {responses.length === 1 ? "" : "s"}
                </div>
                <button type="button" className="chart-drilldown-close" onClick={() => setExpanded(null)}>
                  Close ✕
                </button>
              </div>
              <div className="tbl-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th className="num">Score</th>
                      <th>Feedback</th>
                      <th>Contact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {responses.map((r) => (
                      <tr key={r.response_id}>
                        <td className="name-cell">
                          {topCustomerNames.includes(r.account_name) ? (
                            <a
                              href="#"
                              onClick={(e) => {
                                e.preventDefault();
                                onNavigateToCustomer(r.account_name);
                              }}
                            >
                              {r.account_name}
                            </a>
                          ) : (
                            r.account_name
                          )}
                        </td>
                        <td className="num">{r.score}</td>
                        <td>{r.text || <span className="card-sub">No comment</span>}</td>
                        <td>
                          {r.email ? <a href={`mailto:${r.email}`}>{r.email}</a> : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
