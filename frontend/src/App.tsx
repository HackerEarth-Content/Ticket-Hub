import { useEffect, useRef, useState } from "react";
import "./theme.css";
import "./App.css";
import { ActiveAgentsStrip } from "./components/ActiveAgentsStrip";
import { FrontlineAgentsCard } from "./components/FrontlineAgentsCard";
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
import { FrontlineMetricDashboardCard } from "./components/FrontlineMetricDashboardCard";
import { ResolutionOwnershipCard } from "./components/ResolutionOwnershipCard";
import { AnomaliesCard } from "./components/AnomaliesCard";
import { CustomerOverviewCard } from "./components/CustomerOverviewCard";
import { CustomerVolumeCard } from "./components/CustomerVolumeCard";
import { CustomerStatusCard } from "./components/CustomerStatusCard";
import { CustomerResolverCard } from "./components/CustomerResolverCard";
import { CustomerHealthTable } from "./components/CustomerHealthTable";
import { CustomerExportControl } from "./components/CustomerExportControl";
import { EventExportControl } from "./components/EventExportControl";
import { EventsCard } from "./components/EventsCard";
import { FrontlineLinksCard } from "./components/FrontlineLinksCard";
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
import { useFrontlineAgents } from "./hooks/useFrontlineAgents";
import { useOnShiftNow } from "./hooks/useOnShiftNow";
import { useFrontlineMetricDashboard } from "./hooks/useFrontlineMetricDashboard";
import { useLiveStatus } from "./hooks/useLiveStatus";
import { useTheme } from "./hooks/useTheme";
import type { Period } from "./types";

export default function App() {
  const [period, setPeriod] = useState<Period>("week");
  const [tab, setTab] = useState<DashboardTab>("overview");
  const [showAllCustomerAccounts, setShowAllCustomerAccounts] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportingNps, setExportingNps] = useState(false);
  const [exportingFrontlineMetricDashboard, setExportingFrontlineMetricDashboard] = useState(false);
  const [theme, toggleTheme] = useTheme();
  const { user, logout } = useAuth();
  const { loading, error, data, granularity } = useDashboardData(period, !!user, refreshTick);
  const { live, sync, loading: liveLoading, syncing, syncError, syncNow } = useLiveStatus();
  const { data: frontlineMetricDashboard, loading: frontlineMetricDashboardLoading } =
    useFrontlineMetricDashboard(!!user, refreshTick);
  const { agents, loading: agentsLoading, refresh: refreshAgents } = useFrontlineAgents(!!user);
  const { agents: onShiftAgents, loading: onShiftLoading, refresh: refreshOnShiftNow } = useOnShiftNow();

  // The roster table and the public "on shift now" strip are two separate
  // fetches (one gated, one not) -- any edit in the table (add/remove/edit
  // agent, edit shifts, swap) needs to refresh both, or the strip would sit
  // stale until its next 30s poll.
  function handleAgentsChanged() {
    refreshAgents();
    refreshOnShiftNow();
  }

  // The tab is auth-gated (TabNav drops it from the nav for signed-out
  // visitors) -- if a signed-in user is on it and then signs out, bounce
  // back to overview instead of leaving them on a now-inaccessible tab.
  useEffect(() => {
    if (!user && (tab === "frontline_metrics" || tab === "frontline_agents")) setTab("overview");
  }, [user, tab]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("authError") === "not_allowed") {
      window.alert("Only allowed users can access this dashboard.");
      params.delete("authError");
      const rest = params.toString();
      window.history.replaceState(null, "", window.location.pathname + (rest ? `?${rest}` : ""));
    }
  }, []);

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

  async function handleExportNps() {
    setExportingNps(true);
    try {
      const blob = await api.exportNps(period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nps-report-${period.replace(/:/g, "_")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportingNps(false);
    }
  }

  async function handleExportFrontlineMetricDashboard() {
    setExportingFrontlineMetricDashboard(true);
    try {
      const blob = await api.exportFrontlineMetricDashboard();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "frontline-metric-dashboard.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportingFrontlineMetricDashboard(false);
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
        <ActiveAgentsStrip agents={onShiftAgents} loading={onShiftLoading} />
      </section>

      <TabNav active={tab} onChange={setTab} isLoggedIn={!!user} />

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
            <CsatCard
              csat={data?.csat ?? null}
              unmatchedCsat={data?.unmatchedCsat ?? null}
              loading={loading}
            />
            <DataQualityCard
              dataQuality={data?.dataQuality ?? null}
              uncategorized={data?.uncategorized ?? null}
              loading={loading}
            />
          </div>

          <SectionHeading
            title="NPS"
            color="var(--accent-green)"
            action={
              <button className="section-action" onClick={handleExportNps} disabled={exportingNps}>
                {exportingNps ? "⏳ Exporting…" : "⬇️ Download Excel"}
              </button>
            }
          />
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
            action={<CustomerExportControl period={period} />}
          />
          <CustomerOverviewCard data={data?.customerVolume ?? null} loading={loading} />
          <div className="grid cols-2" style={{ marginBottom: 14 }}>
            <CustomerVolumeCard
              data={data?.customerVolume ?? null}
              loading={loading}
              showAll={showAllCustomerAccounts}
              onToggleAll={setShowAllCustomerAccounts}
            />
            <CustomerStatusCard
              data={data?.customerStatus ?? null}
              loading={loading}
              showAll={showAllCustomerAccounts}
            />
          </div>
          <CustomerResolverCard data={data?.customerDetails ?? null} loading={loading} />
          {user && (
            <div style={{ marginTop: 14 }}>
              <CustomerHealthTable data={data?.customerDetails ?? null} loading={loading} />
            </div>
          )}
        </>
      )}

      {tab === "events" && (
        <>
          <SectionHeading
            title="Programs/Events"
            color="var(--accent-yellow)"
            action={<EventExportControl eventNames={data?.eventVolume?.events.map((e) => e.event_name) ?? []} />}
          />
          <EventsCard data={data?.eventVolume ?? null} loading={loading} />
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
                  label: "Content Requests",
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
              title="Content Requests by reporter"
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

      {tab === "frontline_metrics" && user && (
        <>
          <SectionHeading
            title="Frontline Metric Dashboard"
            color="var(--accent-aqua)"
            action={
              <button
                className="section-action"
                onClick={handleExportFrontlineMetricDashboard}
                disabled={exportingFrontlineMetricDashboard}
              >
                {exportingFrontlineMetricDashboard ? "⏳ Exporting…" : "⬇️ Download Excel"}
              </button>
            }
          />
          <FrontlineMetricDashboardCard
            data={frontlineMetricDashboard}
            loading={frontlineMetricDashboardLoading}
          />
          <div style={{ marginTop: 14 }}>
            <FrontlineLinksCard />
          </div>
        </>
      )}

      {tab === "frontline_agents" && user && (
        <>
          <SectionHeading title="Frontline Agents" color="var(--accent-aqua)" />
          <FrontlineAgentsCard agents={agents} loading={agentsLoading} onChanged={handleAgentsChanged} />
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
