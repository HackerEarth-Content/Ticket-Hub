import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { OnShiftAgent } from "../types";

const POLL_INTERVAL_MS = 30_000;

interface State {
  loading: boolean;
  agents: OnShiftAgent[];
  refresh: () => void;
}

/** Public, unauthenticated -- powers the "On shift now" row inside the live
 * panel for every visitor, not just signed-in users. The backend computes
 * "on shift right now" itself and returns only name/email/phone for
 * those agents, so unlike useFrontlineAgents this never exposes the full
 * roster or anyone's schedule. Polled more tightly (30s) than the full
 * roster since the payload is tiny and it's the only way this strip learns
 * a shift boundary passed. */
export function useOnShiftNow(): State {
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<OnShiftAgent[]>([]);

  const fetchOnce = useCallback(() => {
    return api
      .onShiftNow()
      .then((data) => setAgents(data))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchOnce();
    const id = setInterval(fetchOnce, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchOnce]);

  return { loading, agents, refresh: fetchOnce };
}
