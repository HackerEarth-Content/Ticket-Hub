import { useEffect, useState } from "react";
import { api } from "../api";
import type { DashboardData, Granularity, Period } from "../types";

interface State {
  loading: boolean;
  error: string | null;
  data: DashboardData | null;
  granularity: Granularity;
}

/** today/yesterday (and a single-day custom range) span under 24h -- a
 * "day" bucket collapses the whole period into a single point, which
 * renders as a single dot on a line chart. Use hourly buckets instead. */
function granularityFor(period: Period): Granularity {
  if (period === "today" || period === "yesterday") return "hour";
  if (period.startsWith("custom:")) {
    const [, start, end] = period.split(":");
    return start === end ? "hour" : "day";
  }
  return "day";
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
      api.backlineOverview(period),
      api.aePerformance(period),
      api.escalations(period),
      api.stageTiming(period),
      api.frt(period),
      api.fcr(period),
      api.resolutionOwnership(period),
      api.anomalies(period),
      api.uncategorized(period),
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
          backlineOverview,
          aePerformance,
          escalations,
          stageTiming,
          frt,
          fcr,
          resolutionOwnership,
          anomalies,
          uncategorized,
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
              backlineOverview,
              aePerformance,
              escalations,
              stageTiming,
              frt,
              fcr,
              resolutionOwnership,
              anomalies,
              uncategorized,
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
