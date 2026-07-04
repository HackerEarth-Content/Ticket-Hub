import type {
  AgentKpi,
  Csat,
  DataQuality,
  Granularity,
  LiveToday,
  ModuleDistribution,
  Period,
  Pipelines,
  ResolutionByPriority,
  SlaKpis,
  StageDistribution,
  StatusDistribution,
  Summary,
  SyncNowResult,
  SyncStatus,
  VolumeTrendPoint,
} from "./types";

const BASE = "/dashboard";

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
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

export const api = {
  liveToday: () => get<LiveToday>("/live/today"),
  summary: (period: Period) => get<Summary>("/summary", { period }),
  volumeTrend: (period: Period, granularity: Granularity = "day") =>
    get<VolumeTrendPoint[]>("/volume/trend", { period, granularity }),
  moduleDistribution: (period: Period) =>
    get<ModuleDistribution>("/distribution/module", { period }),
  statusDistribution: (period: Period) =>
    get<StatusDistribution>("/distribution/status", { period }),
  stageDistribution: (period: Period) =>
    get<StageDistribution>("/distribution/stage", { period }),
  resolutionByPriority: (period: Period) =>
    get<ResolutionByPriority>("/kpis/mttr", { period }),
  slaKpis: (period: Period) => get<SlaKpis>("/kpis/sla", { period }),
  csat: (period: Period) => get<Csat>("/kpis/csat", { period }),
  agents: (period: Period) => get<AgentKpi[]>("/kpis/agents", { period }),
  dataQuality: (period: Period) => get<DataQuality>("/kpis/data-quality", { period }),
  syncStatus: () => get<SyncStatus>("/meta/sync-status"),
  syncNow: () => post<SyncNowResult>("/meta/sync-now"),
  pipelines: () => get<Pipelines>("/meta/pipelines"),
};
