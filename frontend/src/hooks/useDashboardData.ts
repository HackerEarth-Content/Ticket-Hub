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

/** Fetches every period-scoped KPI route for a given period. Split into a
 * public group (always fetched, a real failure here is a genuine outage)
 * and a private group (per-agent data, requires sign-in) -- the private
 * group is only attempted when signed in, and never fails the public one:
 * a signed-out visitor should still see the org-wide dashboard. */
export function useDashboardData(period: Period, isLoggedIn: boolean, refreshKey = 0): State {
  const [state, setState] = useState<Omit<State, "granularity">>({
    loading: true,
    error: null,
    data: null,
  });
  const granularity = granularityFor(period);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    const publicData = Promise.all([
      api.summary(period),
      api.volumeTrend(period, granularity),
      api.moduleDistribution(period),
      api.statusDistribution(period),
      api.stageDistribution(period),
      api.sourceDistribution(period),
      api.resolutionByPriority(period),
      api.slaKpis(period),
      api.csat(period),
      api.nps(period),
      api.dataQuality(period),
      api.backlineOverview(period),
      api.stageTiming(period),
      api.frt(period),
      api.fcr(period),
      api.resolutionOwnership(period),
      api.customerVolume(period),
      api.customerStatus(period),
      api.customerDetails(period),
      api.slackIssues(period),
    ]);

    const privateData: Promise<
      [
        DashboardData["agents"],
        DashboardData["aePerformance"],
        DashboardData["escalations"],
        DashboardData["anomalies"],
        DashboardData["uncategorized"],
        DashboardData["moduleTickets"],
        DashboardData["statusTickets"],
      ]
    > = isLoggedIn
      ? Promise.all([
          api.agents(period),
          api.aePerformance(period),
          api.escalations(period),
          api.anomalies(period),
          api.uncategorized(period),
          api.moduleTickets(period),
          api.statusTickets(period),
        ]).catch(() => [[], null, null, null, null, null, null])
      : Promise.resolve([[], null, null, null, null, null, null]);

    Promise.all([publicData, privateData])
      .then(
        ([
          [
            summary,
            volumeTrend,
            moduleDistribution,
            statusDistribution,
            stageDistribution,
            sourceDistribution,
            resolutionByPriority,
            sla,
            csat,
            nps,
            dataQuality,
            backlineOverview,
            stageTiming,
            frt,
            fcr,
            resolutionOwnership,
            customerVolume,
            customerStatus,
            customerDetails,
            slackIssues,
          ],
          [agents, aePerformance, escalations, anomalies, uncategorized, moduleTickets, statusTickets],
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
              sourceDistribution,
              resolutionByPriority,
              sla,
              csat,
              nps,
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
              moduleTickets,
              statusTickets,
              slackIssues,
              customerVolume,
              customerStatus,
              customerDetails,
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
  }, [period, granularity, refreshKey, isLoggedIn]);

  return { ...state, granularity };
}
