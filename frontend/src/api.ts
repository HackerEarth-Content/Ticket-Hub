import type {
  AgentKpi,
  BacklineAePerformance,
  BacklineEscalations,
  BacklineOverview,
  BacklineStageTiming,
  Csat,
  CurrentUser,
  CustomerDetails,
  CustomerStatusBreakdown,
  CustomerVolume,
  DashboardLink,
  DataAnomalies,
  DataQuality,
  AgentShift,
  EventVolume,
  FrontlineAgent,
  FrontlineFcr,
  FrontlineFrt,
  FrontlineMetricDashboard,
  Granularity,
  LiveToday,
  ModuleDistribution,
  ModuleTickets,
  Nps,
  OnShiftAgent,
  Period,
  Pipelines,
  ResolutionByPriority,
  ResolutionOwnership,
  SlackIssues,
  SlackWorkflowIssues,
  SlaKpis,
  SourceDistribution,
  StageDistribution,
  StatusDistribution,
  StatusTickets,
  Summary,
  SyncNowResult,
  SyncStatus,
  UncategorizedTickets,
  UnmatchedCsatResponses,
  VolumeTrendPoint,
} from "./types";

const BASE = "/dashboard";

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new ApiError(`GET ${path} failed: ${res.status} ${res.statusText}`, res.status);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

async function sendJson<T>(method: "POST" | "PUT", path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(`${method} ${path} failed: ${res.status} ${res.statusText}`, res.status);
  }
  return res.json() as Promise<T>;
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    throw new ApiError(`DELETE ${path} failed: ${res.status} ${res.statusText}`, res.status);
  }
}

export const api = {
  liveToday: () => get<LiveToday>("/live/today"),
  summary: (period: Period) => get<Summary>("/summary", { period }),
  volumeTrend: (period: Period, granularity: Granularity = "day") =>
    get<VolumeTrendPoint[]>("/volume/trend", { period, granularity }),
  moduleDistribution: (period: Period) =>
    get<ModuleDistribution>("/distribution/module", { period }),
  moduleTickets: (period: Period) =>
    get<ModuleTickets>("/distribution/module/tickets", { period }),
  statusDistribution: (period: Period) =>
    get<StatusDistribution>("/distribution/status", { period }),
  statusTickets: (period: Period) =>
    get<StatusTickets>("/distribution/status/tickets", { period }),
  stageDistribution: (period: Period) =>
    get<StageDistribution>("/distribution/stage", { period }),
  sourceDistribution: (period: Period) =>
    get<SourceDistribution>("/distribution/source", { period }),
  resolutionByPriority: (period: Period) =>
    get<ResolutionByPriority>("/kpis/mttr", { period }),
  slaKpis: (period: Period) => get<SlaKpis>("/kpis/sla", { period }),
  csat: (period: Period) => get<Csat>("/kpis/csat", { period }),
  nps: (period: Period) => get<Nps>("/kpis/nps", { period }),
  agents: (period: Period) => get<AgentKpi[]>("/kpis/agents", { period }),
  dataQuality: (period: Period) => get<DataQuality>("/kpis/data-quality", { period }),
  backlineOverview: (period: Period) =>
    get<BacklineOverview>("/backline/overview", { period }),
  aePerformance: (period: Period) =>
    get<BacklineAePerformance>("/backline/ae-performance", { period }),
  escalations: (period: Period) =>
    get<BacklineEscalations>("/backline/escalations", { period }),
  slackIssues: (period: Period) => get<SlackIssues>("/slack/issues", { period }),
  slackWorkflowIssues: (period: Period) =>
    get<SlackWorkflowIssues>("/slack/workflow-issues", { period }),
  stageTiming: (period: Period) =>
    get<BacklineStageTiming>("/backline/stage-timing", { period }),
  frt: (period: Period) => get<FrontlineFrt>("/frontline/frt", { period }),
  fcr: (period: Period) => get<FrontlineFcr>("/frontline/fcr", { period }),
  resolutionOwnership: (period: Period) =>
    get<ResolutionOwnership>("/frontline/resolution-ownership", { period }),
  frontlineMetricDashboard: () => get<FrontlineMetricDashboard>("/frontline/metric-dashboard"),
  dashboardLinks: () => get<DashboardLink[]>("/frontline/metric-dashboard/links"),
  addDashboardLink: (name: string, url: string) =>
    sendJson<DashboardLink>("POST", "/frontline/metric-dashboard/links", { name, url }),
  updateDashboardLink: (id: number, name: string, url: string) =>
    sendJson<DashboardLink>("PUT", `/frontline/metric-dashboard/links/${id}`, { name, url }),
  deleteDashboardLink: (id: number) => del(`/frontline/metric-dashboard/links/${id}`),
  frontlineAgents: () => get<FrontlineAgent[]>("/frontline/agents"),
  addFrontlineAgent: (name: string, email: string, phone: string) =>
    sendJson<FrontlineAgent>("POST", "/frontline/agents", { name, email, phone: phone || null }),
  updateFrontlineAgent: (id: number, name: string, email: string, phone: string) =>
    sendJson<FrontlineAgent>("PUT", `/frontline/agents/${id}`, { name, email, phone: phone || null }),
  deleteFrontlineAgent: (id: number) => del(`/frontline/agents/${id}`),
  setFrontlineAgentShifts: (id: number, shifts: AgentShift[]) =>
    sendJson<FrontlineAgent>("PUT", `/frontline/agents/${id}/shifts`, { shifts }),
  swapFrontlineAgentShifts: (agentAId: number, agentBId: number) =>
    sendJson<{ a: FrontlineAgent; b: FrontlineAgent }>("POST", "/frontline/agents/swap", {
      agent_a_id: agentAId,
      agent_b_id: agentBId,
    }),
  onShiftNow: () => get<OnShiftAgent[]>("/frontline/on-shift"),
  anomalies: (period: Period) => get<DataAnomalies>("/quality/anomalies", { period }),
  uncategorized: (period: Period) =>
    get<UncategorizedTickets>("/quality/uncategorized", { period }),
  unmatchedCsat: (period: Period) =>
    get<UnmatchedCsatResponses>("/quality/unmatched-csat", { period }),
  customerVolume: (period: Period) => get<CustomerVolume>("/customers/volume", { period }),
  customerStatus: (period: Period) =>
    get<CustomerStatusBreakdown>("/customers/status", { period }),
  customerDetails: (period: Period) => get<CustomerDetails>("/customers/details", { period }),
  customerNames: () => get<{ customer_names: string[] }>("/customers/names"),
  eventNames: () => get<{ event_names: string[] }>("/events/names"),
  eventVolume: (period: Period) => get<EventVolume>("/events/volume", { period }),
  syncStatus: () => get<SyncStatus>("/meta/sync-status"),
  syncNow: () => post<SyncNowResult>("/meta/sync-now"),
  pipelines: () => get<Pipelines>("/meta/pipelines"),
  exportCustomerCounts: async (period: Period): Promise<Blob> => {
    const res = await fetch(`${BASE}/customers/export?period=${encodeURIComponent(period)}`);
    if (!res.ok) {
      throw new ApiError(
        `GET /customers/export failed: ${res.status} ${res.statusText}`,
        res.status,
      );
    }
    return res.blob();
  },
  exportCustomerTickets: async (period: Period, customerName: string): Promise<Blob> => {
    const url = `${BASE}/customers/export/tickets?period=${encodeURIComponent(period)}&customer_name=${encodeURIComponent(customerName)}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(
        `GET /customers/export/tickets failed: ${res.status} ${res.statusText}`,
        res.status,
      );
    }
    return res.blob();
  },
  exportCustomerList: async (names: string[]): Promise<Blob> => {
    const res = await fetch(`${BASE}/customers/export/by-list`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names }),
    });
    if (!res.ok) {
      throw new ApiError(
        `POST /customers/export/by-list failed: ${res.status} ${res.statusText}`,
        res.status,
      );
    }
    return res.blob();
  },
  exportWorkbook: async (period: Period): Promise<Blob> => {
    const res = await fetch(`${BASE}/export?period=${encodeURIComponent(period)}`);
    if (!res.ok) {
      throw new ApiError(`GET /export failed: ${res.status} ${res.statusText}`, res.status);
    }
    return res.blob();
  },
  exportEventTickets: async (eventName: string): Promise<Blob> => {
    const url = `${BASE}/events/export/tickets?event_name=${encodeURIComponent(eventName)}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(
        `GET /events/export/tickets failed: ${res.status} ${res.statusText}`,
        res.status,
      );
    }
    return res.blob();
  },
  exportFrontlineMetricDashboard: async (): Promise<Blob> => {
    const res = await fetch(`${BASE}/frontline/metric-dashboard/export`);
    if (!res.ok) {
      throw new ApiError(
        `GET /frontline/metric-dashboard/export failed: ${res.status} ${res.statusText}`,
        res.status,
      );
    }
    return res.blob();
  },
  exportNps: async (period: Period): Promise<Blob> => {
    const res = await fetch(`${BASE}/nps/export?period=${encodeURIComponent(period)}`);
    if (!res.ok) {
      throw new ApiError(`GET /nps/export failed: ${res.status} ${res.statusText}`, res.status);
    }
    return res.blob();
  },
};

export { ApiError };

/** Separate from `api` -- these hit /api/auth and /api/users, not /dashboard. */
export const authApi = {
  me: async (): Promise<CurrentUser | null> => {
    const res = await fetch("/api/users/me");
    return res.ok ? ((await res.json()) as CurrentUser) : null;
  },
  logout: () => fetch("/api/auth/logout", { method: "POST" }),
};
