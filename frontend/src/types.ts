export type Period = "today" | "yesterday" | "week" | "month";

export interface LiveToday {
  open_ticket_count_by_status: Record<string, number>;
  resolved_today_count: number;
  sla_breaching_soon_count: number;
  generated_at: string;
}

export interface Summary {
  period: Period;
  period_start: string;
  period_end: string;
  tickets_created_count: number;
  tickets_resolved_count: number;
  median_resolution_time_hours: number | null;
  tickets_resolved_over_48_hours_count: number;
  sla_breach_percentage: number | null;
}

export interface VolumeTrendPoint {
  date: string;
  tickets_created_count: number;
  tickets_resolved_count: number;
}

export interface ModuleDistribution {
  ticket_count_by_module: Record<string, number>;
}

export interface StatusDistribution {
  ticket_count_by_status: Record<string, number>;
}

export interface StageDistribution {
  ticket_count_by_pipeline_and_stage: Record<string, Record<string, number>>;
}

export interface ResolutionByPriority {
  median_resolution_time_hours_by_priority: Record<string, number>;
}

export interface SlaKpis {
  first_response_sla_status_breakdown: Record<string, number>;
  first_response_sla_breach_percentage: number | null;
  resolution_sla_status_breakdown: Record<string, number>;
  resolution_sla_breach_percentage: number | null;
}

export interface Csat {
  total_response_count: number;
  response_count_by_rating: Record<string, number>;
  rating_scale_confirmed: boolean;
}

export interface AgentKpi {
  owner_id: string;
  owner_name: string | null;
  ticket_count: number;
  median_resolution_time_hours: number | null;
}

export interface DataQuality {
  priority_inferred_percentage: number | null;
  uncategorized_ticket_percentage: number | null;
  tickets_pending_over_48_hours_count_by_stage: Record<string, number>;
  tickets_pending_over_48_hours_total: number;
}

export interface SyncStatus {
  last_synced_at: string | null;
  total_ticket_count: number;
}

export interface SyncNowResult extends SyncStatus {
  sync_stats: Record<string, unknown>;
}

export type Granularity = "hour" | "day" | "week" | "month";

export interface PipelineInfo {
  pipeline_id: string;
  pipeline_label: string;
}

export interface Pipelines {
  pipelines: PipelineInfo[];
}

export interface DashboardData {
  summary: Summary;
  volumeTrend: VolumeTrendPoint[];
  moduleDistribution: ModuleDistribution;
  statusDistribution: StatusDistribution;
  stageDistribution: StageDistribution;
  resolutionByPriority: ResolutionByPriority;
  sla: SlaKpis;
  csat: Csat;
  agents: AgentKpi[];
  dataQuality: DataQuality;
}
