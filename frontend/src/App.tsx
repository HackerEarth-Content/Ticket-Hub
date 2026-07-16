import { useEffect, useRef, useState } from "react";
import "./theme.css";
import "./App.css";
import { Header } from "./components/Header";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { SummaryCard } from "./components/SummaryCard";
import { VolumeTrendChart } from "./components/VolumeTrendChart";
import { ModuleDistributionCard } from "./components/ModuleDistributionCard";
import { SourceDistributionCard } from "./components/SourceDistributionCard";
import { StatusDistributionCard } from "./components/StatusDistributionCard";
import { BottleneckTable } from "./components/BottleneckTable";
import { SlaPanel } from "./components/SlaPanel";
import { ResolutionByPriorityCard } from "./components/ResolutionByPriorityCard";
import { AgentLeaderboard } from "./components/AgentLeaderboard";
import { DataQualityCard } from "./components/DataQualityCard";
import { CsatCard } from "./components/CsatCard";
import { NpsCard } from "./components/NpsCard";
import { BacklineOverviewCard } from "./components/BacklineOverviewCard";
import { BacklineAePerformanceCard } from "./components/BacklineAePerformanceCard";
import { EscalationsTable } from "./components/EscalationsTable";
import { StageTimingCard } from "./components/StageTimingCard";
import { FrontlineQualityCard } from "./components/FrontlineQualityCard";
import { ResolutionOwnershipCard } from "./components/ResolutionOwnershipCard";
import { AnomaliesCard } from "./components/AnomaliesCard";
import { CustomerOverviewCard } from "./components/CustomerOverviewCard";
import { CustomerVolumeCard } from "./components/CustomerVolumeCard";
import { CustomerStatusCard } from "./components/CustomerStatusCard";
import { CustomerResolverCard } from "./components/CustomerResolverCard";
import { CustomerHealthTable } from "./components/CustomerHealthTable";
import { ContentOnCallTable } from "./components/ContentOnCallTable";
import { BarListCard } from "./components/BarListCard";
import { SlackOverviewCard } from "./components/SlackOverviewCard";
import { SlackPriorityCard } from "./components/SlackPriorityCard";
import { SlackReporterPieChart } from "./components/SlackReporterPieChart";
import { SectionHeading } from "./components/SectionHeading";
import { TabNav, type DashboardTab } from "./components/TabNav";
import { api } from "./api";
import { useAuth } from "./hooks/useAuth";
import { useDashboardData } from "./hooks/useDashboardData";
import { useLiveStatus } from "./hooks/useLiveStatus";
import { useTheme } from "./hooks/useTheme";
import type { Period } from "./types";

export default function App() {
  const [period, setPeriod] = useState<Period>("week");
  const [tab, setTab] = useState<DashboardTab>("overview");
  const [refreshTick, setRefreshTick] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportingCustomers, setExportingCustomers] = useState(false);
  const [theme, toggleTheme] = useTheme();
  const { user, logout } = useAuth();
  const { loading, error, data, granularity } = useDashboardData(period, !!user, refreshTick);
  const { live, sync, loading: liveLoading, syncing, syncError, syncNow } = useLiveStatus();

  // The status poll (60s) notices when the backend's 5-min scheduled sync
  // lands; refetch the dashboard data then, instead of on a blind timer.
  // The ref skips the first non-null value so mount doesn't double-fetch.
  const lastSyncedAt = sync?.last_synced_at ?? null;
  const prevSyncedAt = useRef<string | null>(null);
  useEffect(() => {
    if (lastSyncedAt && prevSyncedAt.current) setRefreshTick((t) => t + 1);
    prevSyncedAt.current = lastSyncedAt;
  }, [lastSyncedAt]);

  async function handleSyncNow() {
    // No manual refresh bump -- syncNow updates last_synced_at, which the
    // effect above turns into a data refetch.
    await syncNow();
  }

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await api.exportWorkbook(period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `helpdesk-export-${period.replace(/:/g, "_")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportCustomers() {
    setExportingCustomers(true);
    try {
      const blob = await api.exportCustomerCounts(period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `customer-issues-${period.replace(/:/g, "_")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportingCustomers(false);
    }
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
        user={user}
        onLogout={logout}
        onExport={handleExport}
        exporting={exporting}
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
          <span className="live-panel-title">Live updates</span>
          <span className="live-panel-sub">
            always current &middot; independent of the date range above
          </span>
        </div>
        <LiveStatusStrip live={live} loading={liveLoading} />
      </section>

      <TabNav active={tab} onChange={setTab} />

      {tab === "overview" && (
        <>
          <SectionHeading title="Overview" color="var(--accent-blue)" />
          <SummaryCard
            summary={data?.summary ?? null}
            csatResponses={data?.csat.total_response_count ?? null}
            loading={loading}
          />

          <SectionHeading title="Volume & Distribution" color="var(--accent-indigo)" />
          <VolumeTrendChart
            data={data?.volumeTrend ?? []}
            loading={loading}
            granularity={granularity}
          />
          <div className="grid cols-2" style={{ margin: "14px 0" }}>
            <ModuleDistributionCard
              distribution={data?.moduleDistribution ?? null}
              moduleTickets={data?.moduleTickets ?? null}
              loading={loading}
            />
            <SourceDistributionCard distribution={data?.sourceDistribution ?? null} loading={loading} />
          </div>

          <StatusDistributionCard
            distribution={data?.statusDistribution ?? null}
            statusTickets={data?.statusTickets ?? null}
            loading={loading}
          />

          <BottleneckTable stageDistribution={data?.stageDistribution ?? null} loading={loading} />

          <SectionHeading title="SLA & Resolution Priority" color="var(--accent-yellow)" />
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <SlaPanel sla={data?.sla ?? null} loading={loading} />
            <ResolutionByPriorityCard data={data?.resolutionByPriority ?? null} loading={loading} />
          </div>

          <SectionHeading title="Service Health" color="var(--accent-magenta)" />
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <CsatCard csat={data?.csat ?? null} loading={loading} />
            <DataQualityCard
              dataQuality={data?.dataQuality ?? null}
              uncategorized={data?.uncategorized ?? null}
              loading={loading}
            />
          </div>

          <SectionHeading title="NPS" color="var(--accent-green)" />
          <NpsCard
            nps={data?.nps ?? null}
            loading={loading}
            topCustomerNames={data?.customerVolume?.top_customers.map((c) => c.customer_name) ?? []}
            onNavigateToCustomer={() => setTab("customers")}
          />
        </>
      )}

      {tab === "frontline" && (
        <>
          <SectionHeading title="Frontline Quality" color="var(--accent-aqua)" />
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <FrontlineQualityCard frt={data?.frt ?? null} fcr={data?.fcr ?? null} loading={loading} />
            <ResolutionOwnershipCard data={data?.resolutionOwnership ?? null} loading={loading} />
          </div>

          {user && (
            <>
              <SectionHeading title="Team Performance" color="var(--accent-aqua)" />
              <AgentLeaderboard agents={data?.agents ?? []} loading={loading} />
              <div style={{ marginTop: 14 }}>
                <AnomaliesCard data={data?.anomalies ?? null} loading={loading} />
              </div>
            </>
          )}
        </>
      )}

      {tab === "backline" && (
        <>
          <SectionHeading title="Backline Operations" color="var(--accent-orange)" />
          <BacklineOverviewCard data={data?.backlineOverview ?? null} loading={loading} />
          <div className="grid cols-2" style={{ margin: "14px 0" }}>
            <StageTimingCard data={data?.stageTiming ?? null} loading={loading} />
            {user && <BacklineAePerformanceCard data={data?.aePerformance ?? null} loading={loading} />}
          </div>

          {user && (
            <>
              <SectionHeading title="Escalations" color="var(--accent-red)" />
              <EscalationsTable data={data?.escalations ?? null} loading={loading} />
            </>
          )}
        </>
      )}

      {tab === "customers" && (
        <>
          <SectionHeading
            title="Customers"
            color="var(--accent-indigo)"
            action={
              <button
                className="section-action"
                onClick={handleExportCustomers}
                disabled={exportingCustomers}
              >
                {exportingCustomers ? "⏳ Exporting…" : "⬇️ Download Excel"}
              </button>
            }
          />
          <CustomerOverviewCard data={data?.customerVolume ?? null} loading={loading} />
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <CustomerVolumeCard data={data?.customerVolume ?? null} loading={loading} />
            <CustomerStatusCard data={data?.customerStatus ?? null} loading={loading} />
          </div>
          <CustomerResolverCard data={data?.customerDetails ?? null} loading={loading} />
          <div style={{ marginTop: 14 }}>
            <CustomerHealthTable data={data?.customerDetails ?? null} loading={loading} />
          </div>
        </>
      )}

      {tab === "content_oncall" && (
        <>
          <SectionHeading title="Content/engg On-call" color="var(--accent-magenta)" />
          <SlackOverviewCard data={data?.slackIssues ?? null} loading={loading} />
          <div style={{ marginBottom: 14 }}>
            <BarListCard
              title="Issues by team"
              sub="Slack-reported issues split by workflow team"
              loading={loading}
              emptyLabel="No Slack-reported issues in this period."
              items={[
                {
                  label: "Content",
                  value: data?.slackIssues?.tickets_by_workflow_category.content.count ?? 0,
                  color: "var(--accent-magenta)",
                },
                {
                  label: "Engg Oncall",
                  value: data?.slackIssues?.tickets_by_workflow_category.engg_oncall.count ?? 0,
                  color: "var(--accent-blue)",
                },
                {
                  label: "Uncategorized",
                  value: data?.slackIssues?.tickets_by_workflow_category.uncategorized.count ?? 0,
                  color: "var(--ink-3)",
                },
              ].filter((i) => i.value > 0)}
            />
          </div>
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <SlackReporterPieChart
              data={data?.slackWorkflowIssues?.content.by_reporter ?? []}
              loading={loading}
              title="Content issues by reporter"
              emptyLabel="No Content-workflow issues in this period."
            />
            <SlackReporterPieChart
              data={data?.slackWorkflowIssues?.engg_oncall.by_reporter ?? []}
              loading={loading}
              title="Engg Oncall issues by reporter"
              emptyLabel="No Engg Oncall-workflow issues in this period."
            />
          </div>
          <SectionHeading title="Priority" color="var(--accent-yellow)" />
          <SlackPriorityCard data={data?.slackIssues ?? null} loading={loading} />

          <div style={{ marginTop: 14 }}>
            <ContentOnCallTable data={data?.slackIssues ?? null} loading={loading} />
          </div>
        </>
      )}

      <footer className="note">
        <span>
          Source: HubSpot Support &middot; synced via <code>hubspot_pipeline</code>
        </span>
      </footer>
    </div>
  );
}
