import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { FrontlineAgent } from "../types";

const POLL_INTERVAL_MS = 60_000;

interface State {
  loading: boolean;
  agents: FrontlineAgent[];
  refresh: () => void;
}

/** The full shift roster (every agent's email, Slack ID, whole week) --
 * team-only, powers the Frontline Agents tab only. Skips the fetch entirely
 * when signed out, since the backend would 401 it anyway. The public "On
 * shift now" strip uses useOnShiftNow instead, which exposes far less. */
export function useFrontlineAgents(isLoggedIn: boolean): State {
  const [loading, setLoading] = useState(isLoggedIn);
  const [agents, setAgents] = useState<FrontlineAgent[]>([]);

  const fetchOnce = useCallback(() => {
    if (!isLoggedIn) {
      setAgents([]);
      setLoading(false);
      return Promise.resolve();
    }
    return api
      .frontlineAgents()
      .then((data) => setAgents(data))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, [isLoggedIn]);

  useEffect(() => {
    setLoading(isLoggedIn);
    fetchOnce();
    if (!isLoggedIn) return;
    const id = setInterval(fetchOnce, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isLoggedIn, fetchOnce]);

  return { loading, agents, refresh: fetchOnce };
}
