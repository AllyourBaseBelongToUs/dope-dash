// Report generation types

// Import types from index.ts to maintain single source of truth
import type { ReportFormat as ReportFormatBase, ReportSchedule as ReportScheduleBase } from './index';

// Re-export with extended values for reports module
export type ReportFormat = ReportFormatBase;
export type ReportSchedule = 'daily' | 'weekly' | 'monthly' | 'none'; // FIXED: Added 'monthly' for reports, kept 'none' for compatibility
export type ReportType = 'session' | 'trends' | 'comparison' | 'error_analysis';
export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface ReportConfig {
  id?: string; // Optional for creation, required for saved configs
  type: ReportType;
  format: ReportFormat;
  title: string;
  includeCharts: boolean;
  sessionIds?: string[];
  dateRange?: string; // Simple string like "7d", "30d", "90d"
  dateFrom?: string; // ISO date string
  dateTo?: string; // ISO date string
  // Extended fields for advanced functionality
  dateRangeObject?: {
    from: string;
    to: string;
  };
  compareSessionIds?: string[];
}

export interface ReportData {
  title: string;
  generatedAt: string;
  type: ReportType;
  format: ReportFormat;
  sessions?: SessionSummary[];
  trends?: TrendData;
  comparison?: ComparisonData;
  errorAnalysis?: ErrorAnalysisData;
  charts?: ChartData[];
}

export interface SessionSummary {
  sessionId: string;
  agentType: string;
  projectName: string;
  status: string;
  startedAt: string;
  endedAt?: string;
  duration: number;
  totalSpecs: number;
  completedSpecs: number;
  failedSpecs: number;
  specSuccessRate: number;
  totalEvents: number;
  errorCount: number;
  warningCount: number;
  eventBreakdown: Record<string, number>;
}

export interface TrendData {
  period: string;
  bucketSize: string;
  fromDate: string;
  toDate: string;
  totalSessions: number;
  sessionsByStatus: Record<string, number>;
  sessionsByAgent: Record<string, number>;
  sessionTrend: TimeSeriesPoint[];
  specTrend: SpecTimeSeriesPoint[];
  errorTrend: TimeSeriesPoint[];
  avgSessionDuration: number;
  totalSpecRuns: number;
  specSuccessRate: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  count: number;
}

export interface SpecTimeSeriesPoint {
  timestamp: string;
  total: number;
  completed: number;
  failed: number;
}

export interface ComparisonData {
  sessions: SessionSummary[];
  metrics: ComparisonMetrics;
}

export interface ComparisonMetrics {
  totalSessions: number;
  avgDuration: number;
  avgSpecSuccessRate: number;
  totalSpecs: number;
  totalErrors: number;
  fastestSession?: {
    sessionId: string;
    duration: number;
  };
  slowestSession?: {
    sessionId: string;
    duration: number;
  };
  highestSuccessRate?: {
    sessionId: string;
    rate: number;
  };
  lowestSuccessRate?: {
    sessionId: string;
    rate: number;
  };
}

export interface ErrorAnalysisData {
  totalErrors: number;
  errorFrequency: Record<string, number>;
  topErrors: Array<{
    message: string;
    count: number;
    sessions: string[];
  }>;
  errorsBySession: Array<{
    sessionId: string;
    projectName: string;
    errorCount: number;
    mostRecentError: string;
  }>;
  errorTrend: TimeSeriesPoint[];
}

export interface ChartData {
  type: 'line' | 'bar' | 'pie' | 'area';
  title: string;
  data: Record<string, unknown>;
  xAxisKey?: string;
  yAxisKey?: string;
  config?: Record<string, unknown>;
}

export interface Report {
  id: string;
  title: string;
  type: ReportType;
  format: ReportFormat;
  status: ReportStatus;
  config: ReportConfig;
  data?: ReportData;
  filePath?: string;
  fileSize?: number;
  createdAt: string;
  completedAt?: string;
  error?: string;
  scheduled?: boolean;
  schedule?: ReportSchedule;
  nextRunAt?: string;
}

export interface ReportScheduleConfig {
  enabled: boolean;
  frequency: ReportSchedule;
  reportTypes: ReportType[];
  format: ReportFormat;
  time?: string; // HH:MM format for daily/weekly
  dayOfWeek?: number; // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  retentionDays: number;
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  type: ReportType;
  defaultFormat: ReportFormat;
  config: Partial<ReportConfig>;
}

// Simplified data type interfaces for basic report functionality
export interface SessionSummaryBasic {
  sessionId: string;
  projectName: string;
  agentType: string;
  status: string;
  startedAt: string;
  duration: number;
  eventCounts: Record<string, number>;
  specRuns?: number;
  errors?: number;
}

export interface TrendDataBasic {
  date: string;
  sessionCount: number;
  totalDuration: number;
  errorRate: number;
  avgDuration: number;
}

export interface ComparisonDataBasic {
  sessionId: string;
  projectName: string;
  agentType: string;
  duration: number;
  eventCount: number;
  errorCount: number;
}

export interface ErrorAnalysisBasic {
  sessionId: string;
  projectName: string;
  errorType: string;
  count: number;
  lastSeen: string;
}

export interface ReportScheduleConfigBasic {
  enabled: boolean;
  frequency: ReportSchedule;
  time: string;
  dayOfWeek?: number;
  recipients: string[];
}

