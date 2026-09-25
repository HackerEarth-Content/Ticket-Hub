export type Period = "today" | "yesterday" | "week" | "month" | `custom:${string}:${string}`;

export interface CurrentUser {
  id: string;
  email: string;
  name: string | null;
}

export interface LiveToday {
  open_ticket_count_by_status: Record<string, number>;
  resolved_today_count: number;
  resolved_today_on_time_count: number;
  resolved_today_on_time_percentage: number | null;
  first_response_on_time_today_count: number;
  first_response_on_time_today_percentage: number | null;
  generated_at: string;
}

export interface Summary {
  period: Period;
  period_start: string;
  period_end: string;
  tickets_created_count: number;
  tickets_resolved_count: number;
  median_resolution_time_hours: number | null;
  mean_resolution_time_hours: number | null;
  tickets_resolved_within_48_hours_count: number;
  resolved_within_48_hours_percentage: number | null;
  resolution_within_72_hours_percentage: number | null;
  same_day_resolved_count: number;
  same_day_median_resolution_time_hours: number | null;
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

export interface DrilldownTicket {
  ticket_id: string;
  subject: string;
  canonical_status?: string;
  module?: string;
  owner_name: string | null;
}

export interface TicketDrilldownGroup {
  count: number;
  tickets: DrilldownTicket[];
  truncated: boolean;
}

export interface ModuleTickets {
  tickets_by_module: Record<string, TicketDrilldownGroup>;
}

export interface StatusTickets {
  tickets_by_status: Record<string, TicketDrilldownGroup>;
}

export interface StageDistribution {
  ticket_count_by_pipeline_and_stage: Record<string, Record<string, number>>;
}

export interface ResolutionByPriority {
  median_resolution_time_hours_by_priority: Record<string, number>;
  resolved_ticket_count_by_priority: Record<string, number>;
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
  normalized_csat_percentage: number | null;
  unmatched_to_ticket_count: number;
  rating_scale_confirmed: boolean;
}

export interface UnmatchedCsatResponse {
  submission_id: string;
  rating: number;
  submitted_at: string;
  contact_id: string | null;
}

export interface UnmatchedCsatResponses {
  unmatched_count: number;
  responses: UnmatchedCsatResponse[];
  truncated: boolean;
}

export type NpsBucket = "promoter" | "passive" | "detractor";

export interface NpsResponseDetail {
  response_id: string;
  account_name: string;
  score: number;
  email: string | null;
  text: string | null;
}

export interface Nps {
  total_response_count: number;
  promoter_count: number;
  passive_count: number;
  detractor_count: number;
  response_count_by_score: Record<string, number>;
  nps_score: number | null;
  responses_by_bucket: Record<NpsBucket, NpsResponseDetail[]>;
}

export interface AgentKpi {
  owner_id: string;
  owner_name: string | null;
  ticket_count: number;
  actionable_count: number;
  non_actionable_count: number;
  closed_count: number;
  still_open_count: number;
  closure_rate_percentage: number | null;
  median_resolution_time_hours: number | null;
  mean_resolution_time_hours: number | null;
  first_response_sla_on_time_count: number;
  first_response_sla_missed_count: number;
  first_response_sla_on_time_percentage: number | null;
  first_contact_resolution_true_count: number;
  first_contact_resolution_percentage: number | null;
  backline_escalation_count: number;
  backline_escalation_percentage: number | null;
  resolved_by_backline_engineering_count: number;
  escalated_to_engineering_count: number;
  csat_response_count: number;
  csat_normalized_percentage: number | null;
}

export interface NumericStats {
  average: number | null;
  median: number | null;
  minimum: number | null;
  maximum: number | null;
}

export interface AePerformance {
  backline_engineer: string;
  tickets_handled_count: number;
  tickets_resolved_count: number;
  all_resolved: boolean;
  path_breakdown: Record<string, number>;
  ae_stage_time_hours: NumericStats;
  ae_stage_time_hours_by_path: Record<string, NumericStats>;
  ticket_resolution_time_hours: NumericStats;
  ticket_resolution_time_hours_by_path: Record<string, NumericStats>;
  escalated_to_engineering_count: number;
  high_priority_ticket_count: number;
  frontline_owners_supported_count: number;
  categories_handled_count: number;
}

export interface BacklineAePerformance {
  ae_performance: AePerformance[];
}

export interface Escalation {
  ticket_id: string;
  subject: string;
  owner_name: string | null;
  backline_engineer: string | null;
  escalation_path: string;
  canonical_status: string;
  final_resolution: string | null;
  entered_at: string | null;
  exited_at: string | null;
  cumulative_time_hours: number | null;
  live_wait_time_hours: number | null;
  jira_link: string | null;
}

export interface BacklineEscalations {
  escalation_count: number;
  escalations: Escalation[];
  truncated: boolean;
}

export interface SlackIssue {
  ticket_id: string;
  subject: string;
  reporter_name: string;
  reporter_is_fallback_owner: boolean;
  owner_name: string | null;
  stage_label: string;
  created_at: string | null;
  closed_at: string | null;
  priority: string;
  team: string;
  channel: string;
  ticket_validity: string | null;
}

export interface SlackReporterCounts {
  reporter_name: string;
  reported_count: number;
  solved_count: number;
}

export interface SlackWorkflowTicketGroup {
  count: number;
  tickets: SlackIssue[];
  truncated: boolean;
}

export interface SlackIssues {
  issue_count: number;
  issues: SlackIssue[];
  truncated: boolean;
  issue_count_by_priority: Record<string, number>;
  issue_count_by_channel: Record<string, number>;
  priority_by_team: Record<string, Record<string, number>>;
  priority_by_channel: Record<string, Record<string, number>>;
  by_reporter: SlackReporterCounts[];
  tickets_by_workflow_category: {
    content: SlackWorkflowTicketGroup;
    engg_oncall: SlackWorkflowTicketGroup;
    uncategorized: SlackWorkflowTicketGroup;
  };
}

export interface SlackWorkflowBucket {
  issue_count: number;
  by_reporter: SlackReporterCounts[];
}

export interface SlackWorkflowIssues {
  content: SlackWorkflowBucket;
  engg_oncall: SlackWorkflowBucket;
}

export interface StageTimingEntry {
  label: string;
  entered_count: number;
  exited_count: number;
  still_in_queue_count: number;
  average_cumulative_time_hours: number | null;
  minimum_cumulative_time_hours: number | null;
  maximum_cumulative_time_hours: number | null;
  max_live_wait_time_hours: number | null;
}

export interface BacklineStageTiming {
  stage_timing: Record<string, StageTimingEntry>;
}

export interface BacklineOverview {
  total_ticket_count: number;
  actionable_ticket_count: number;
  actionable_percentage: number | null;
  closed_ticket_count: number;
  closed_percentage_of_actionable: number | null;
  still_open_ticket_count: number;
  resolved_by_backline_count: number;
  resolved_by_backline_percentage_of_actionable: number | null;
  escalated_to_engineering_count: number;
  escalated_to_engineering_percentage_of_actionable: number | null;
  fcr_true_count: number;
  fcr_percentage_of_actionable: number | null;
  final_resolution_breakdown: Record<string, number>;
  final_resolution_percentage_of_closed: Record<string, number | null>;
}

export interface FrontlineFrtByOwner {
  owner_id: string;
  owner_name: string | null;
  on_time_count: number;
  missed_count: number;
  awaiting_reply_overdue_count: number;
  on_time_percentage: number | null;
}

export interface FrontlineFrt {
  sla_threshold_minutes: number;
  on_time_count: number;
  missed_count: number;
  awaiting_reply_overdue_count: number;
  on_time_percentage: number | null;
  by_owner: FrontlineFrtByOwner[];
}

export interface FrontlineFcr {
  fcr_true_count: number;
  fcr_false_count: number;
  first_contact_resolution_percentage: number | null;
  fcr_resolved_within_24_hours_count: number;
  fcr_resolved_within_24_hours_percentage: number | null;
}

export interface ResolutionOwnership {
  ticket_count_by_resolution_bucket: Record<string, number>;
  percentage_of_resolved_by_bucket: Record<string, number | null>;
}

export interface AnomalyTicket {
  ticket_id: string;
  subject: string;
  canonical_status: string;
  module: string;
  final_resolution: string | null;
  owner_name: string | null;
}

export interface AnomalyGroup {
  label: string;
  count: number;
  tickets: AnomalyTicket[];
  truncated: boolean;
}

export interface DataAnomalies {
  anomaly_count_by_type: Record<string, number>;
  total_anomaly_count: number;
  anomalies_by_type: Record<string, AnomalyGroup>;
}

export interface UncategorizedTicket {
  ticket_id: string;
  subject: string;
  owner_name: string | null;
  final_resolution: string | null;
  created_at: string | null;
}

export interface UncategorizedTickets {
  uncategorized_count: number;
  tickets: UncategorizedTicket[];
  truncated: boolean;
}

export interface DataQuality {
  priority_inferred_percentage: number | null;
  uncategorized_ticket_percentage: number | null;
}

export type FrontlineMetricFormat = "number" | "percent" | "hours" | "days" | "score";

export interface FrontlineMetricDefinition {
  key: string;
  label: string;
  format: FrontlineMetricFormat;
  target: string;
  note?: string;
}

export interface FrontlineMetricGroup {
  key: string;
  label: string;
  metrics: FrontlineMetricDefinition[];
}

export type FrontlineMetricValues = Record<string, number | null>;

export interface FrontlineMetricQuarter {
  code: string;
  label: string;
  month_labels: string[];
  months: FrontlineMetricValues[];
  achieved: FrontlineMetricValues;
}

export interface FrontlineMetricDashboard {
  quarters: FrontlineMetricQuarter[];
  groups: FrontlineMetricGroup[];
}

export interface DashboardLink {
  id: number;
  name: string;
  url: string;
}

export interface AgentShift {
  day_of_week: number; // 0=Monday .. 6=Sunday
  is_week_off: boolean;
  is_holiday: boolean;
  start_time: string | null; // "HH:MM", IST wall-clock
  end_time: string | null; // "HH:MM"; < start_time means it crosses midnight
}

export interface FrontlineAgent {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  shifts: AgentShift[]; // always 7 entries, one per day_of_week
}

// Public counterpart of FrontlineAgent -- only agents on shift right now,
// and only the fields the "On shift now" strip needs (no schedule).
export interface OnShiftAgent {
  id: number;
  name: string;
  email: string;
  phone: string | null;
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

export interface CustomerVolumeEntry {
  customer_name: string;
  ticket_count: number;
}

export interface CustomerVolume {
  top_customers: CustomerVolumeEntry[];
  all_customers: CustomerVolumeEntry[];
  other_identified_customer_count: number;
  other_identified_ticket_count: number;
  identified_customer_count: number;
  identified_ticket_count: number;
  no_account_ticket_count: number;
  total_ticket_count: number;
}

export interface CustomerStatusEntry {
  customer_name: string;
  status_counts: Record<string, number>;
  stage_counts: Record<string, number>;
}

export interface CustomerStatusBreakdown {
  customers: CustomerStatusEntry[];
  all_customers: CustomerStatusEntry[];
}

export interface EventVolumeEntry {
  event_name: string;
  ticket_count: number;
}

export interface EventVolume {
  events: EventVolumeEntry[];
}

export interface SourceDistribution {
  by_source: Record<string, number>;
  total_ticket_count: number;
}

export interface CustomerDetailsEntry {
  customer_name: string;
  resolution_bucket_counts: Record<string, number>;
  priority_counts: Record<string, number>;
  sla_met_count: number;
  sla_breached_count: number;
  median_resolution_time_hours: number | null;
  median_first_response_hours: number | null;
  escalated_count: number;
  escalated_percentage: number | null;
  open_backlog_count: number;
}

export interface CustomerDetails {
  customers: CustomerDetailsEntry[];
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
  nps: Nps;
  // Team-only (require sign-in) -- null when signed out, not just "not yet loaded".
  agents: AgentKpi[];
  aePerformance: BacklineAePerformance | null;
  escalations: BacklineEscalations | null;
  anomalies: DataAnomalies | null;
  uncategorized: UncategorizedTickets | null;
  unmatchedCsat: UnmatchedCsatResponses | null;
  moduleTickets: ModuleTickets | null;
  statusTickets: StatusTickets | null;
  slackIssues: SlackIssues | null;
  slackWorkflowIssues: SlackWorkflowIssues;

  dataQuality: DataQuality;
  stageTiming: BacklineStageTiming;
  backlineOverview: BacklineOverview;
  frt: FrontlineFrt;
  fcr: FrontlineFcr;
  resolutionOwnership: ResolutionOwnership;
  customerVolume: CustomerVolume;
  customerStatus: CustomerStatusBreakdown;
  customerDetails: CustomerDetails;
  sourceDistribution: SourceDistribution;
  eventVolume: EventVolume;
}
