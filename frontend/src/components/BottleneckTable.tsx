import type { StageDistribution } from "../types";

interface Row {
  pipeline: string;
  stage: string;
  count: number;
}

function buildRows(stageDistribution: StageDistribution | null): Row[] {
  if (!stageDistribution) return [];
  const rows: Row[] = [];

  for (const [pipeline, stages] of Object.entries(
    stageDistribution.ticket_count_by_pipeline_and_stage
  )) {
    for (const [stage, count] of Object.entries(stages)) {
      // Every team-routing "Pending on X" stage -- these collapse into one
      // "Pending" bucket everywhere else on the dashboard, which is exactly
      // what hides which team is the bottleneck.
      if (!/pending/i.test(stage)) continue;
      rows.push({ pipeline, stage, count });
    }
  }

  return rows.sort((a, b) => b.count - a.count);
}

interface Props {
  stageDistribution: StageDistribution | null;
  loading: boolean;
}

export function BottleneckTable({ stageDistribution, loading }: Props) {
  const rows = buildRows(stageDistribution);

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="card-head">
        <div>
          <div className="card-title">Tickets by pending stage, by team</div>
          <div className="card-sub">
            Every "Pending on…" stage, broken out for this period — collapsed into one
            "Pending" bucket everywhere else on this page. For which of these are stuck &gt;48h
            right now (independent of the date range above), see the live panel up top.
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
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.pipeline}-${r.stage}`}>
                  <td className="pipeline-tag">{r.pipeline}</td>
                  <td className="stage-name">{r.stage}</td>
                  <td className="num">{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
