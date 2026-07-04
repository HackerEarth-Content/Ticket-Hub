import { useEffect, useState } from "react";
import { api } from "../api";
import type { DashboardData, Granularity, Period } from "../types";

interface State {
  loading: boolean;
  error: string | null;
  data: DashboardData | null;
  granularity: Granularity;
}

/** today/yesterday span under 24h -- a "day" bucket collapses the whole
 * period into a single point, which renders as a single dot on a line
 * chart. Use hourly buckets for those two periods instead. */
function granularityFor(period: Period): Granularity {
  return period === "today" || period === "yesterday" ? "hour" : "day";
}

/** Fetches every period-scoped KPI route together for a given period.
 * `refreshKey` is an escape hatch to force a refetch (e.g. after a manual
 * "sync now") without waiting for `period` to change. */
export function useDashboardData(period: Period, refreshKey = 0): State {
  const [state, setState] = useState<Omit<State, "granularity">>({
    loading: true,
    error: null,
    data: null,
  });
  const granularity = granularityFor(period);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    Promise.all([
      api.summary(period),
      api.volumeTrend(period, granularity),
      api.moduleDistribution(period),
      api.statusDistribution(period),
      api.stageDistribution(period),
      api.resolutionByPriority(period),
      api.slaKpis(period),
      api.csat(period),
      api.agents(period),
      api.dataQuality(period),
    ])
      .then(
        ([
          summary,
          volumeTrend,
          moduleDistribution,
          statusDistribution,
          stageDistribution,
          resolutionByPriority,
          sla,
          csat,
          agents,
          dataQuality,
        ]) => {
          if (cancelled) return;
          setState({
            loading: false,
            error: null,
            data: {
              summary,
              volumeTrend,
              moduleDistribution,
              statusDistribution,
              stageDistribution,
              resolutionByPriority,
              sla,
              csat,
              agents,
              dataQuality,
            },
          });
        }
      )
      .catch((err: Error) => {
        if (cancelled) return;
        setState({ loading: false, error: err.message, data: null });
      });

    return () => {
      cancelled = true;
    };
  }, [period, granularity, refreshKey]);

  return { ...state, granularity };
}
