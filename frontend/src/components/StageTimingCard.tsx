import type { BacklineStageTiming } from "../types";
import { formatHours, formatNumber } from "../format";

interface Props {
  data: BacklineStageTiming | null;
  loading: boolean;
}

export function StageTimingCard({ data, loading }: Props) {
  const stages = Object.values(data?.stage_timing ?? {});

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Backline stage timing</div>
          <div className="card-sub">Entered / still queued / avg-min-max time / live wait, per stage</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 140, width: "100%" }} />
      ) : stages.length === 0 ? (
        <div className="card-sub">No backline activity in this period.</div>
      ) : (
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Stage</th>
                <th className="num">Entered</th>
                <th className="num">Still queued</th>
                <th className="num">Avg time in stage</th>
                <th className="num">Min time in stage</th>
                <th className="num">Max time in stage</th>
                <th className="num">Max live wait</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((s) => (
                <tr key={s.label}>
                  <td className="stage-name">{s.label}</td>
                  <td className="num">{formatNumber(s.entered_count)}</td>
                  <td className="num">
                    {s.still_in_queue_count > 0 ? (
                      <span className="chip warning">{s.still_in_queue_count}</span>
                    ) : (
                      0
                    )}
                  </td>
                  <td className="num">{formatHours(s.average_cumulative_time_hours)}</td>
                  <td className="num">{formatHours(s.minimum_cumulative_time_hours)}</td>
                  <td className="num">{formatHours(s.maximum_cumulative_time_hours)}</td>
                  <td className="num">{formatHours(s.max_live_wait_time_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
