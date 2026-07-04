import { useState } from "react";
import "./theme.css";
import "./App.css";
import { Header } from "./components/Header";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { SummaryCard } from "./components/SummaryCard";
import { VolumeTrendChart } from "./components/VolumeTrendChart";
import { ModuleDistributionCard } from "./components/ModuleDistributionCard";
import { StatusDistributionCard } from "./components/StatusDistributionCard";
import { BottleneckTable } from "./components/BottleneckTable";
import { SlaPanel } from "./components/SlaPanel";
import { ResolutionByPriorityCard } from "./components/ResolutionByPriorityCard";
import { AgentLeaderboard } from "./components/AgentLeaderboard";
import { DataQualityCard } from "./components/DataQualityCard";
import { CsatCard } from "./components/CsatCard";
import { useDashboardData } from "./hooks/useDashboardData";
import { useLiveStatus } from "./hooks/useLiveStatus";
import { useTheme } from "./hooks/useTheme";
import type { Period } from "./types";

export default function App() {
  const [period, setPeriod] = useState<Period>("week");
  const [refreshTick, setRefreshTick] = useState(0);
  const [theme, toggleTheme] = useTheme();
  const { loading, error, data, granularity } = useDashboardData(period, refreshTick);
  const { live, sync, loading: liveLoading, syncing, syncError, syncNow } = useLiveStatus();

  async function handleSyncNow() {
    await syncNow();
    setRefreshTick((t) => t + 1);
  }

  return (
    <div className="wrap">
      <Header
        period={period}
        onPeriodChange={setPeriod}
        sync={sync}
        syncing={syncing}
        syncError={syncError}
        onSyncNow={handleSyncNow}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {error && (
        <div className="error-banner">
          Couldn't reach the dashboard API — {error}. Is the backend running (
          <code>uvicorn main:app</code>)?
        </div>
      )}

      <LiveStatusStrip live={live} loading={liveLoading} />

      <SummaryCard
        summary={data?.summary ?? null}
        csatResponses={data?.csat.total_response_count ?? null}
        loading={loading}
      />

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <VolumeTrendChart data={data?.volumeTrend ?? []} loading={loading} granularity={granularity} />
        <ModuleDistributionCard distribution={data?.moduleDistribution ?? null} loading={loading} />
      </div>

      <StatusDistributionCard distribution={data?.statusDistribution ?? null} loading={loading} />

      <BottleneckTable
        stageDistribution={data?.stageDistribution ?? null}
        dataQuality={data?.dataQuality ?? null}
        loading={loading}
      />

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <SlaPanel sla={data?.sla ?? null} loading={loading} />
        <ResolutionByPriorityCard data={data?.resolutionByPriority ?? null} loading={loading} />
      </div>

      <div className="grid cols-2">
        <AgentLeaderboard agents={data?.agents ?? []} loading={loading} />
        <div className="grid" style={{ gap: 14 }}>
          <DataQualityCard dataQuality={data?.dataQuality ?? null} loading={loading} />
          <CsatCard csat={data?.csat ?? null} loading={loading} />
        </div>
      </div>

      <footer className="note">
        <span>
          Source: HubSpot Support &middot; GT Support &middot; Customer Success &middot;
          Marketing pipelines, synced via <code>hubspot_pipeline</code>
        </span>
      </footer>
    </div>
  );
}
