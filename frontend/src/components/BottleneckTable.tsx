import type { DataQuality, StageDistribution } from "../types";

interface Row {
  pipeline: string;
  stage: string;
  count: number;
  stuckOver48h: number;
}

function buildRows(
  stageDistribution: StageDistribution | null,
  dataQuality: DataQuality | null
): Row[] {
  if (!stageDistribution) return [];
  const stuckByStage = dataQuality?.tickets_pending_over_48_hours_count_by_stage ?? {};
  const rows: Row[] = [];

  for (const [pipeline, stages] of Object.entries(
    stageDistribution.ticket_count_by_pipeline_and_stage
  )) {
    for (const [stage, count] of Object.entries(stages)) {
      // Every team-routing "Pending on X" stage -- these collapse into one
      // "Pending" bucket everywhere else on the dashboard, which is exactly
      // what hides which team is the bottleneck.
      if (!/pending/i.test(stage)) continue;
      rows.push({ pipeline, stage, count, stuckOver48h: stuckByStage[stage] ?? 0 });
    }
  }

  return rows.sort((a, b) => b.count - a.count);
}

function stuckChip(n: number) {
  if (n === 0) return <span className="num">0</span>;
  const tone = n > 2 ? "serious" : "warning";
  return (
    <span className="num">
      <span className={`chip ${tone}`}>{n}</span>
    </span>
  );
}

interface Props {
  stageDistribution: StageDistribution | null;
  dataQuality: DataQuality | null;
  loading: boolean;
}

export function BottleneckTable({ stageDistribution, dataQuality, loading }: Props) {
  const rows = buildRows(stageDistribution, dataQuality);

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div>
          <div className="card-title">Where tickets are stuck, by team</div>
          <div className="card-sub">
            Every "Pending on…" stage, broken out — collapsed into one "Pending" bucket
            everywhere else on this page
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 160, width: "100%" }} />
      ) : rows.length === 0 ? (
        <div className="card-sub">No team-routed pending stages in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Pipeline</th>
                <th>Stage</th>
                <th className="num">Tickets</th>
                <th className="num">Stuck &gt;48h</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.pipeline}-${r.stage}`}>
                  <td className="pipeline-tag">{r.pipeline}</td>
                  <td className="stage-name">{r.stage}</td>
                  <td className="num">{r.count}</td>
                  <td>{stuckChip(r.stuckOver48h)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
