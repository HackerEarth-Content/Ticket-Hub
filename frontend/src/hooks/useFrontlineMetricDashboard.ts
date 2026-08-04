import { useEffect, useState } from "react";
import { api } from "../api";
import type { FrontlineMetricDashboard } from "../types";

interface State {
  loading: boolean;
  data: FrontlineMetricDashboard | null;
}

/** Quarterly FRT/FCR/TTR/CSAT/NPS rollup -- independent of the period
 * selector (same convention as useLiveStatus), so it only refetches on
 * mount and when a sync lands (refreshKey), not on every period change.
 * Team-only, like the tab it powers -- skips the fetch entirely when signed
 * out rather than pulling this heavier, multi-query endpoint for nothing. */
export function useFrontlineMetricDashboard(isLoggedIn: boolean, refreshKey = 0): State {
  const [state, setState] = useState<State>({ loading: isLoggedIn, data: null });

  useEffect(() => {
    if (!isLoggedIn) {
      setState({ loading: false, data: null });
      return;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true }));
    api
      .frontlineMetricDashboard()
      .then((data) => {
        if (!cancelled) setState({ loading: false, data });
      })
      .catch(() => {
        if (!cancelled) setState({ loading: false, data: null });
      });
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn, refreshKey]);

  return state;
}
