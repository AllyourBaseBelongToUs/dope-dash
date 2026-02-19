// Dashboard types for real-time progress display

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'polling';

export type EventType =
  | 'spec_start'
  | 'spec_complete'
  | 'spec_fail'
  | 'error'
  | 'progress'
  | 'session_start'
  | 'session_end'
  | 'process_crash'
  | 'process_restart'
  | 'atom_start'
  | 'atom_complete'
  | 'iteration_start'
  | 'iteration_complete'
  | 'subtask_start'
  | 'subtask_complete';

export interface WebSocketMessage {
  type: 'event' | 'ping' | 'pong' | 'error' | 'info' | 'quota_update' | 'quota_alert' | 'rate_limit_update' | 'rate_limit_detected' | 'rate_limit_resolved' | 'rate_limit_failed';
  id?: string;
  session_id?: string;
  event_type?: EventType;
  data?: Record<string, unknown>;
  created_at?: string;
  message?: string;
}

export interface SpecProgress {
  specName: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  duration?: number;
}

export type AgentStatus = 'running' | 'paused' | 'stopped';

export type AgentType = 'ralph' | 'claude' | 'cursor' | 'terminal' | 'crawler' | 'analyzer' | 'reporter' | 'tester' | 'custom';

// FIXED: Renamed to avoid duplication with CommandHistoryEntry below
// This is the simplified version for dashboard control commands
export interface DashboardCommandEntry {
  commandId: string;
  command: 'pause' | 'resume' | 'skip' | 'stop';
  status: 'pending' | 'acknowledged' | 'completed' | 'failed' | 'timeout';
  createdAt: string;
  error?: string;
}

export interface Session {
  id: string;
  agentType: AgentType;
  projectName: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  endedAt?: string;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, unknown>;
  specs: SpecProgress[];
  currentSpec?: string;
  completedSpecs: number;
  totalSpecs: number;
  progress: number;
  lastActivity?: string;
  error?: string;
  agentStatus?: AgentStatus;
  commandHistory?: DashboardCommandEntry[]; // FIXED: Use renamed type
  errorCount?: number;
  lastErrors?: ErrorEvent[];
  // Agent runtime metadata
  pid?: number;
  workingDir?: string;
  command?: string;
  lastHeartbeat?: string;
  tmuxSession?: string;
}

export interface ErrorEvent {
  id: string;
  sessionId: string;
  eventType: 'error' | 'spec_fail';
  message: string;
  stackTrace?: string;
  data: Record<string, unknown>;
  createdAt: string;
  dismissed?: boolean;
}

export interface ErrorAggregation {
  totalErrors: number;
  errorFrequency: Record<string, number>;
  bySession: Array<{
    session_id: string;
    error_count: number;
    most_recent_error?: {
      id: string;
      event_type: string;
      message: string;
      created_at: string;
    };
  }>;
  sessionsWithErrors: number;
}

export interface QueryFilters {
  session_id?: string;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface Event {
  id: string;
  sessionId: string;
  eventType: EventType;
  data: Record<string, unknown>;
  createdAt: string;
}

export interface DashboardState {
  sessions: Session[];
  events: Event[];
  connectionStatus: ConnectionStatus;
  activeSessionId: string | null;
  lastEventId: string | null;
  error: string | null;
}

// Notification types
export type NotificationType = 'spec_complete' | 'error' | 'agent_stopped';

export type NotificationPreference = 'all' | 'errors' | 'none';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  sessionId?: string;
  timestamp: string;
  read: boolean;
}

export interface NotificationSettings {
  soundEnabled: boolean;
  preferences: NotificationPreference;
  desktopEnabled: boolean;
}

// Environment types
export type EnvironmentType = 'vm' | 'local' | 'unknown';

export interface EnvironmentInfo {
  type: EnvironmentType;
  hostname: string;
  platform: string;
  userAgent: string;
  detectedAt: string;
  networkInfo: {
    isPrivateIP: boolean;
    isLocalhost: boolean;
  };
}

export interface EnvironmentConfig {
  wsUrl: string;
  apiUrl: string;
  controlApiUrl: string;
}

export interface EnvironmentState {
  current: EnvironmentInfo | null;
  previous: EnvironmentInfo | null;
  config: EnvironmentConfig | null;
  transitionCount: number;
}

// Report/Analytics types
// FIXED: Consolidated ReportFormat - now includes 'json' for comprehensive report export
export type ReportFormat = 'markdown' | 'pdf' | 'json';
export type ReportSchedule = 'daily' | 'weekly' | 'none';

export interface ReportMetricData {
  label: string;
  value: number;
  timestamp?: string;
}

export interface SessionMetrics {
  sessionId: string;
  projectName: string;
  agentType: AgentType;
  status: Session['status'];
  duration: number;
  startedAt: string;
  completedAt?: string;
  specsCompleted: number;
  specsTotal: number;
  errorCount: number;
  specCompletionRate: number;
}

export interface ErrorRateMetric {
  date: string;
  errorCount: number;
  sessionCount: number;
  errorRate: number;
}

export interface SpecCompletionMetric {
  specName: string;
  avgDuration: number;
  successRate: number;
  failureCount: number;
  totalRuns: number;
}

export interface AgentPerformanceMetric {
  agentType: AgentType;
  sessionCount: number;
  avgDuration: number;
  successRate: number;
  errorCount: number;
}

export interface ReportData {
  generatedAt: string;
  dateRange: {
    start: string;
    end: string;
  };
  summary: {
    totalSessions: number;
    completedSessions: number;
    failedSessions: number;
    cancelledSessions: number;
    totalErrors: number;
    avgSessionDuration: number;
  };
  sessionMetrics: SessionMetrics[];
  errorRateMetrics: ErrorRateMetric[];
  specCompletionMetrics: SpecCompletionMetric[];
  agentPerformanceMetrics: AgentPerformanceMetric[];
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  schedule: ReportSchedule;
  formats: ReportFormat[];
  includeCharts: boolean;
  includeSessionDetails: boolean;
  includeErrorSummary: boolean;
  includeSpecResults: boolean;
  dateRangeDays: number;
  createdAt: string;
  updatedAt: string;
}

export interface GeneratedReport {
  id: string;
  templateId: string;
  title: string;
  format: ReportFormat;
  generatedAt: string;
  dateRange: {
    start: string;
    end: string;
  };
  filePath: string;
  fileSize: number;
  downloadUrl: string;
}

export interface ReportScheduleConfig {
  enabled: boolean;
  frequency: ReportSchedule;
  time: string; // HH:MM format
  timezone: string;
  templates: string[]; // template IDs
  lastRunAt?: string;
  nextRunAt?: string;
}

// Portfolio/Project types
export type ProjectStatus = 'idle' | 'running' | 'paused' | 'error' | 'completed';
export type ProjectPriority = 'low' | 'medium' | 'high' | 'critical';

export type ProjectControlAction = 'pause' | 'resume' | 'skip' | 'stop' | 'retry' | 'restart';
export type ProjectControlStatus = 'pending' | 'acknowledged' | 'completed' | 'failed' | 'timeout';

export interface ProjectControlHistoryEntry {
  id: string;
  action: ProjectControlAction;
  status: ProjectControlStatus;
  initiatedBy: string;
  agentsAffected: number;
  errorMessage?: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  priority: ProjectPriority;
  description?: string;
  progress: number;
  totalSpecs: number;
  completedSpecs: number;
  activeAgents: number;
  lastActivityAt?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export interface ProjectSummary {
  totalProjects: number;
  projectsByStatus: Record<ProjectStatus, number>;
  projectsByPriority: Record<ProjectPriority, number>;
  totalActiveAgents: number;
  avgProgress: number;
  totalSpecs: number;
  completedSpecs: number;
  overallCompletionRate: number;
  recentActiveProjects: number;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectDetail extends Project {
  stats: {
    totalSessions: number;
    activeSessions: number;
  };
  recentSessions: Array<{
    id: string;
    agentType: AgentType;
    status: Session['status'];
    startedAt?: string;
    endedAt?: string;
    createdAt: string;
  }>;
  controlHistory?: ProjectControlHistoryEntry[];
}

// Command History types
export type CommandStatus = 'pending' | 'sent' | 'acknowledged' | 'completed' | 'failed' | 'timeout';

export interface CommandHistoryEntry {
  id: string;
  projectId?: string;
  sessionId?: string;
  command: string;
  status: CommandStatus;
  result?: string;
  errorMessage?: string;
  exitCode?: number;
  durationMs?: number;
  isFavorite: boolean;
  templateName?: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface CommandHistoryListResponse {
  commands: CommandHistoryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface CommandTemplate {
  id: string;
  name: string;
  description: string;
  command: string;
  category: string;
  tags: string[];
}

export interface SendCommandRequest {
  command: string;
  projectId?: string;
  sessionId?: string;
  templateName?: string;
}

export interface ReplayCommandRequest {
  commandId: string;
}

export interface ToggleFavoriteRequest {
  isFavorite: boolean;
}

export interface CommandHistoryFilters {
  projectId?: string;
  sessionId?: string;
  status?: CommandStatus;
  isFavorite?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CommandStatsSummary {
  totalCommands: number;
  byStatus: Record<CommandStatus, number>;
  totalFavorites: number;
  recentCommands24h: number;
  avgDurationMs: number;
}

// Quota tracking types
export interface QuotaUsage {
  id: string;
  provider_id: string;
  provider_name: string;
  project_id: string | null;
  model: string;
  current_requests: number;
  current_tokens: number;
  max_requests: number;
  max_tokens: number;
  quota_limit: number;
  quota_limit_tokens?: number;
  usage_percent: number;
  is_over_limit: boolean;
  remaining_requests: number;
  remaining_tokens: number;
  time_until_reset_seconds?: number;
  overage_count?: number;
  period_start: string;
  period_end: string;
  last_updated: string;
}

export interface QuotaAlert {
  id: string;
  provider_id: string;
  provider_name: string;
  type: 'warning' | 'critical' | 'exceeded';
  alert_type: 'warning' | 'critical' | 'overage';
  status: 'active' | 'acknowledged' | 'resolved';
  metric: 'requests' | 'tokens' | 'cost';
  threshold: number;
  threshold_percent: number;
  current_value: number;
  current_usage: number;
  quota_limit: number;
  message: string;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface QuotaSummary {
  total_providers: number;
  active_providers: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  total_usage_percent: number;
  alerts_count: number;
  alerts_critical: number;
  critical_alerts_count: number;
  providers_over_limit: number;
  last_updated: string;
}

export interface Provider {
  id: string;
  name: string;
  display_name: string;
  api_endpoint?: string;
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
  rate_limit_tokens_per_day?: number;
  models: string[];
  enabled: boolean;
  priority: number;
}

// Rate Limit tracking types
export interface RateLimitEvent {
  id: string;
  provider_id: string;
  provider_name: string;
  model: string;
  status: 'detected' | 'retrying' | 'resolved' | 'failed';
  retry_count: number;
  attempt_number: number;
  max_attempts: number;
  max_retries: number;
  calculated_backoff_seconds?: number;
  jitter_seconds?: number;
  http_status_code?: number;
  request_method?: string;
  request_endpoint?: string;
  retry_after_seconds?: number;
  next_retry_at: string | null;
  detected_at: string;
  resolved_at: string | null;
  failed_at?: string;
  error_message?: string;
  metadata: Record<string, unknown>;
}

export interface RateLimitEventSummary {
  total_events: number;
  active_events: number;
  resolved_events: number;
  failed_events: number;
  total_retries: number;
  avg_resolution_time_ms: number;
  last_updated: string;
}
