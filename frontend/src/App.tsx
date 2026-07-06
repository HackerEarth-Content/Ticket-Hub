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
import { BacklineOverviewCard } from "./components/BacklineOverviewCard";
import { BacklineAePerformanceCard } from "./components/BacklineAePerformanceCard";
import { EscalationsTable } from "./components/EscalationsTable";
import { StageTimingCard } from "./components/StageTimingCard";
import { FrontlineQualityCard } from "./components/FrontlineQualityCard";
import { ResolutionOwnershipCard } from "./components/ResolutionOwnershipCard";
import { AnomaliesCard } from "./components/AnomaliesCard";
import { SectionHeading } from "./components/SectionHeading";
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

      <section className="live-panel">
        <div className="live-panel-head">
          <span className="live-dot" />
          <span className="live-panel-title">Today's live updates</span>
          <span className="live-panel-sub">
            always current &middot; independent of the date range above
          </span>
        </div>
        <LiveStatusStrip live={live} loading={liveLoading} />
      </section>

      <SectionHeading title="Overview" color="var(--accent-blue)" />
      <SummaryCard
        summary={data?.summary ?? null}
        csatResponses={data?.csat.total_response_count ?? null}
        loading={loading}
      />

      <SectionHeading title="Volume & Distribution" color="var(--accent-indigo)" />
      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <VolumeTrendChart data={data?.volumeTrend ?? []} loading={loading} granularity={granularity} />
        <ModuleDistributionCard distribution={data?.moduleDistribution ?? null} loading={loading} />
      </div>

      <StatusDistributionCard distribution={data?.statusDistribution ?? null} loading={loading} />

      <BottleneckTable stageDistribution={data?.stageDistribution ?? null} loading={loading} />

      <SectionHeading title="SLA & Resolution Priority" color="var(--accent-yellow)" />
      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <SlaPanel sla={data?.sla ?? null} loading={loading} />
        <ResolutionByPriorityCard data={data?.resolutionByPriority ?? null} loading={loading} />
      </div>

      <SectionHeading title="Team Performance & Quality" color="var(--accent-magenta)" />
      <div className="grid cols-2">
        <AgentLeaderboard agents={data?.agents ?? []} loading={loading} />
        <div className="grid" style={{ gap: 14 }}>
          <DataQualityCard
            dataQuality={data?.dataQuality ?? null}
            uncategorized={data?.uncategorized ?? null}
            loading={loading}
          />
          <CsatCard csat={data?.csat ?? null} loading={loading} />
        </div>
      </div>

      <SectionHeading title="Frontline Quality" color="var(--accent-aqua)" />
      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <FrontlineQualityCard frt={data?.frt ?? null} fcr={data?.fcr ?? null} loading={loading} />
        <ResolutionOwnershipCard data={data?.resolutionOwnership ?? null} loading={loading} />
      </div>

      <SectionHeading title="Backline Operations" color="var(--accent-orange)" />
      <BacklineOverviewCard data={data?.backlineOverview ?? null} loading={loading} />

      <div className="grid cols-2" style={{ margin: "14px 0" }}>
        <BacklineAePerformanceCard data={data?.aePerformance ?? null} loading={loading} />
        <StageTimingCard data={data?.stageTiming ?? null} loading={loading} />
      </div>

      <SectionHeading title="Escalations & Data Integrity" color="var(--accent-red)" />
      <EscalationsTable data={data?.escalations ?? null} loading={loading} />

      <div style={{ marginTop: 14 }}>
        <AnomaliesCard data={data?.anomalies ?? null} loading={loading} />
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
