import type {
  ReportConfig,
  ReportData,
  SessionSummary,
  TrendData,
  ComparisonData,
  ComparisonMetrics,
  ErrorAnalysisData,
} from '@/types/reports';

/**
 * Analytics Data Fetcher
 * Fetches data from the Analytics API for report generation
 * Includes retry logic for transient failures
 */

// Default retry configuration
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1000; // ms

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetch with retry logic
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  maxRetries: number = DEFAULT_MAX_RETRIES
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);

      // Retry on 5xx errors and network errors
      if (response.status >= 500 || response.status === 0) {
        if (attempt < maxRetries) {
          await sleep(DEFAULT_RETRY_DELAY * Math.pow(2, attempt)); // Exponential backoff
          continue;
        }
      }

      return response;
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxRetries) {
        await sleep(DEFAULT_RETRY_DELAY * Math.pow(2, attempt));
        continue;
      }
    }
  }

  throw lastError || new Error('Max retries exceeded');
}

interface SessionSummaryResponse {
  session_id: string;
  agent_type: string;
  project_name: string;
  status: string;
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  total_events: number;
  event_type_counts: Record<string, number>;
  total_specs: number;
  completed_specs: number;
  failed_specs: number;
  spec_success_rate: number;
  error_count: number;
  warning_count: number;
  metric_summary?: {
    min?: number;
    max?: number;
    avg?: number;
  };
}

interface TrendsResponse {
  period: string;
  bucket_size: string;
  from_date: string;
  to_date: string;
  total_sessions: number;
  sessions_by_status: Record<string, number>;
  sessions_by_agent: Record<string, number>;
  session_trend: Array<{ timestamp: string; count: number }>;
  spec_trend: Array<{ timestamp: string; total: number; completed: number; failed: number }>;
  error_trend: Array<{ timestamp: string; count: number }>;
  avg_session_duration: number;
  total_spec_runs: number;
  spec_success_rate: number;
}

interface CompareResponse {
  sessions: SessionSummaryResponse[];
  metrics: {
    total_sessions: number;
    avg_duration: number;
    avg_spec_success_rate: number;
    total_specs: number;
    total_errors: number;
    fastest_session?: { session_id: string; duration: number };
    slowest_session?: { session_id: string; duration: number };
    highest_success_rate?: { session_id: string; rate: number };
    lowest_success_rate?: { session_id: string; rate: number };
  };
}

interface ErrorAggregation {
  total_errors: number;
  error_frequency: Record<string, number>;
  by_session: Array<{
    session_id: string;
    error_count: number;
    most_recent_error?: {
      id: string;
      event_type: string;
      message: string;
      created_at: string;
    };
  }>;
  sessions_with_errors: number;
}

/**
 * Get the API base URL from environment config or fallback
 */
function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Check for environment config in localStorage
    const envConfigStr = localStorage.getItem('dope-dash-env-config');
    if (envConfigStr) {
      try {
        const envConfig = JSON.parse(envConfigStr);
        if (envConfig.apiUrl) {
          return envConfig.apiUrl;
        }
      } catch (e) {
        console.warn('Failed to parse env config:', e);
      }
    }

    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
  }
  return 'http://localhost:8000';
}

/**
 * Fetch session summary from analytics API with retry logic
 */
export async function fetchSessionSummary(sessionId: string): Promise<SessionSummary> {
  const baseUrl = getApiBaseUrl();

  try {
    const response = await fetchWithRetry(
      `${baseUrl}/api/analytics/${sessionId}/summary`,
      {
        signal: AbortSignal.timeout(10000), // 10 second timeout
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Session ${sessionId} not found. It may not have been started yet.`);
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to fetch session summary: ${errorData.detail || response.statusText}`);
    }

    const data: SessionSummaryResponse = await response.json();

    return {
      sessionId: data.session_id,
      agentType: data.agent_type,
      projectName: data.project_name,
      status: data.status,
      startedAt: data.started_at,
      endedAt: data.ended_at,
      duration: (data.duration_seconds || 0) * 1000, // Convert to milliseconds
      totalSpecs: data.total_specs,
      completedSpecs: data.completed_specs,
      failedSpecs: data.failed_specs,
      specSuccessRate: data.spec_success_rate,
      totalEvents: data.total_events,
      errorCount: data.error_count,
      warningCount: data.warning_count,
      eventBreakdown: data.event_type_counts,
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Unknown error fetching session summary for ${sessionId}`);
  }
}

/**
 * Fetch trends data from analytics API with retry logic
 */
export async function fetchTrendsData(
  period: number = 30,
  bucketSize: string = 'day'
): Promise<TrendData> {
  const baseUrl = getApiBaseUrl();

  try {
    const response = await fetchWithRetry(
      `${baseUrl}/api/analytics/trends?period=${period}&bucket_size=${bucketSize}`,
      {
        signal: AbortSignal.timeout(15000), // 15 second timeout for trends
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to fetch trends: ${errorData.detail || response.statusText}`);
    }

    const data: TrendsResponse = await response.json();

    return {
      period: data.period,
      bucketSize: data.bucket_size,
      fromDate: data.from_date,
      toDate: data.to_date,
      totalSessions: data.total_sessions,
      sessionsByStatus: data.sessions_by_status,
      sessionsByAgent: data.sessions_by_agent,
      sessionTrend: data.session_trend,
      specTrend: data.spec_trend,
      errorTrend: data.error_trend,
      avgSessionDuration: data.avg_session_duration * 1000, // Convert to milliseconds
      totalSpecRuns: data.total_spec_runs,
      specSuccessRate: data.spec_success_rate,
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Unknown error fetching trends data');
  }
}

/**
 * Fetch comparison data from analytics API with retry logic
 */
export async function fetchComparisonData(sessionIds: string[]): Promise<ComparisonData> {
  const baseUrl = getApiBaseUrl();

  try {
    const response = await fetchWithRetry(`${baseUrl}/api/analytics/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_ids: sessionIds }),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`One or more sessions not found. Please verify the session IDs.`);
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to fetch comparison: ${errorData.detail || response.statusText}`);
    }

    const data: CompareResponse = await response.json();

    const sessions: SessionSummary[] = data.sessions.map((s) => ({
      sessionId: s.session_id,
      agentType: s.agent_type,
      projectName: s.project_name,
      status: s.status,
      startedAt: s.started_at,
      endedAt: s.ended_at,
      duration: (s.duration_seconds || 0) * 1000, // Convert to milliseconds
      totalSpecs: s.total_specs,
      completedSpecs: s.completed_specs,
      failedSpecs: s.failed_specs,
      specSuccessRate: s.spec_success_rate,
      totalEvents: s.total_events,
      errorCount: s.error_count,
      warningCount: s.warning_count,
      eventBreakdown: s.event_type_counts,
    }));

    const metrics: ComparisonMetrics = {
      totalSessions: data.metrics.total_sessions,
      avgDuration: data.metrics.avg_duration * 1000, // Convert to milliseconds
      avgSpecSuccessRate: data.metrics.avg_spec_success_rate,
      totalSpecs: data.metrics.total_specs,
      totalErrors: data.metrics.total_errors,
      fastestSession: data.metrics.fastest_session
        ? {
            sessionId: data.metrics.fastest_session.session_id,
            duration: data.metrics.fastest_session.duration,
          }
        : undefined,
      slowestSession: data.metrics.slowest_session
        ? {
            sessionId: data.metrics.slowest_session.session_id,
            duration: data.metrics.slowest_session.duration,
          }
        : undefined,
      highestSuccessRate: data.metrics.highest_success_rate
        ? {
            sessionId: data.metrics.highest_success_rate.session_id,
            rate: data.metrics.highest_success_rate.rate,
          }
        : undefined,
      lowestSuccessRate: data.metrics.lowest_success_rate
        ? {
            sessionId: data.metrics.lowest_success_rate.session_id,
            rate: data.metrics.lowest_success_rate.rate,
          }
        : undefined,
    };

    return { sessions, metrics };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Unknown error fetching comparison data');
  }
}

/**
 * Fetch error analysis data from analytics API with retry logic
 */
export async function fetchErrorAnalysisData(
  sessionIds?: string[],
  dateRange?: { from: string; to: string }
): Promise<ErrorAnalysisData> {
  const baseUrl = getApiBaseUrl();

  // Build query parameters
  const params = new URLSearchParams();
  if (dateRange) {
    params.append('from_date', dateRange.from);
    params.append('to_date', dateRange.to);
  }

  try {
    const response = await fetchWithRetry(
      `${baseUrl}/api/analytics/errors/aggregated${params.toString() ? `?${params}` : ''}`,
      {
        signal: AbortSignal.timeout(15000),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to fetch error analysis: ${errorData.detail || response.statusText}`);
    }

    const data: ErrorAggregation = await response.json();

    // Process top errors
    const topErrors = Object.entries(data.error_frequency)
      .map(([message, count]) => ({
        message,
        count,
        sessions: data.by_session
          .filter((s) => s.most_recent_error?.message === message)
          .map((s) => s.session_id),
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    const errorsBySession = data.by_session.map((s) => ({
      sessionId: s.session_id,
      projectName: `Session ${s.session_id.slice(0, 8)}`,
      errorCount: s.error_count,
      mostRecentError: s.most_recent_error?.message || 'N/A',
    }));

    return {
      totalErrors: data.total_errors,
      errorFrequency: data.error_frequency,
      topErrors,
      errorsBySession,
      errorTrend: [], // Would need to fetch from trends endpoint
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Unknown error fetching error analysis data');
  }
}

/**
 * Main function to fetch analytics data based on report config
 */
export async function fetchAnalyticsData(config: ReportConfig): Promise<Omit<ReportData, 'title' | 'generatedAt' | 'type' | 'format'>> {
  switch (config.type) {
    case 'session':
      if (!config.sessionIds || config.sessionIds.length === 0) {
        throw new Error('Session IDs required for session report');
      }
      const sessions = await Promise.all(
        config.sessionIds.map((id) => fetchSessionSummary(id))
      );
      return { sessions };

    case 'trends':
      const period = config.dateRangeObject
        ? Math.ceil(
            (new Date(config.dateRangeObject.to).getTime() -
              new Date(config.dateRangeObject.from).getTime()) /
              (1000 * 60 * 60 * 24)
          )
        : 30;
      const trends = await fetchTrendsData(period);
      return { trends };

    case 'comparison':
      if (!config.compareSessionIds || config.compareSessionIds.length === 0) {
        throw new Error('Session IDs required for comparison report');
      }
      const comparison = await fetchComparisonData(config.compareSessionIds);
      return { comparison };

    case 'error_analysis':
      const errorAnalysis = await fetchErrorAnalysisData(config.sessionIds, config.dateRangeObject);
      return { errorAnalysis };

    default:
      throw new Error(`Unsupported report type: ${config.type}`);
  }
}
