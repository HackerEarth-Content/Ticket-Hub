import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { LiveToday, SyncStatus } from "../types";

const POLL_INTERVAL_MS = 60_000;

interface State {
  loading: boolean;
  live: LiveToday | null;
  sync: SyncStatus | null;
  syncing: boolean;
  syncError: string | null;
  syncNow: () => Promise<void>;
}

/** Polls the always-current widgets (live status, sync freshness) on an interval,
 * independent of the period selector -- these aren't period-scoped. */
export function useLiveStatus(): State {
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState<LiveToday | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const fetchOnce = useCallback(() => {
    return Promise.all([api.liveToday(), api.syncStatus()])
      .then(([liveData, syncData]) => {
        setLive(liveData);
        setSync(syncData);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchOnce();
    const id = setInterval(fetchOnce, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchOnce]);

  const syncNow = useCallback(async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const result = await api.syncNow();
      setSync({ last_synced_at: result.last_synced_at, total_ticket_count: result.total_ticket_count });
      await fetchOnce();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [fetchOnce]);

  return { loading, live, sync, syncing, syncError, syncNow };
}
