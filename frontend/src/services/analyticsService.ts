import type {
  ReportData,
  ReportFormat,
  SessionMetrics,
  ErrorRateMetric,
  SpecCompletionMetric,
  AgentPerformanceMetric,
  QueryFilters,
} from '@/types';

/**
 * Analytics Service
 * Handles fetching analytics data and generating reports
 * FIXED: Added request caching and deduplication
 */
class AnalyticsService {
  private baseUrl: string = '';
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private pendingRequests: Map<string, Promise<any>> = new Map();
  private readonly CACHE_TTL = 30000; // 30 seconds cache

  constructor() {
    if (typeof window !== 'undefined') {
      this.baseUrl = this.getApiBaseUrl();
    }
  }

  /**
   * Get cached data if available and not expired
   */
  private getCached<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
      return cached.data as T;
    }
    return null;
  }

  /**
   * Set cache with current timestamp
   */
  private setCache(key: string, data: any): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  /**
   * Fetch with caching and deduplication
   */
  private async fetchWithCache<T>(
    key: string,
    fetcher: () => Promise<T>
  ): Promise<T> {
    // Check cache first
    const cached = this.getCached<T>(key);
    if (cached !== null) {
      return cached;
    }

    // Check if there's a pending request for the same key (deduplication)
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending;
    }

    // Create new request
    const promise = fetcher().then((data) => {
      this.setCache(key, data);
      this.pendingRequests.delete(key);
      return data;
    }).finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  /**
   * Get the API base URL from environment store or fallback
   */
  private getApiBaseUrl(): string {
    // Check environment variable first (Analytics API on port 8004)
    if (process.env.NEXT_PUBLIC_ANALYTICS_API_URL) {
      return process.env.NEXT_PUBLIC_ANALYTICS_API_URL;
    }

    // Try to get from environment config
    try {
      const envConfig = localStorage.getItem('dope-dash-env-config');
      if (envConfig) {
        try {
          const config = JSON.parse(envConfig);
          return config.analyticsApiUrl || config.apiUrl || this.getDefaultApiUrl();
        } catch (e) {
          console.warn('Failed to parse env config:', e);
        }
      }
    } catch (e) {
      // FIXED: Handle localStorage errors (quota, access denied, etc.)
      console.warn('Failed to access localStorage:', e);
    }
    return this.getDefaultApiUrl();
  }

  /**
   * Get default API URL based on current environment
   * Defaults to Analytics API (port 8004)
   */
  private getDefaultApiUrl(): string {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8004';
      }
    }
    return 'http://localhost:8004';
  }

  /**
   * Fetch sessions with analytics data
   * Uses Analytics API (port 8004) - /api/analytics/{session_id}/summary endpoint
   * FIXED: Added caching and proper error handling for empty returns
   */
  async fetchSessions(filters?: QueryFilters): Promise<SessionMetrics[]> {
    const cacheKey = `sessions-${JSON.stringify(filters || {})}`;

    return this.fetchWithCache(cacheKey, async () => {
      try {
        // If specific session_id is provided, use the session summary endpoint
        if (filters?.session_id) {
          const response = await fetch(`${this.baseUrl}/api/analytics/${filters.session_id}/summary`);
          if (!response.ok) {
            throw new Error(`Failed to fetch session summary: ${response.statusText}`);
          }
          const sessionData = await response.json();
          return [this.transformAnalyticsSummaryToMetrics(sessionData)];
        }

        // Otherwise use trends endpoint for session lists
        const params = new URLSearchParams();
        if (filters?.start_date) params.append('start_date', filters.start_date);
        if (filters?.end_date) params.append('end_date', filters.end_date);

        const response = await fetch(`${this.baseUrl}/api/analytics/trends?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch analytics trends: ${response.statusText}`);
        }

        const data = await response.json();

        // FIXED: Instead of returning empty array, try to extract session data from trends
        // If the API returns sessions array, use it; otherwise return empty with proper handling
        if (data.sessions && Array.isArray(data.sessions)) {
          return data.sessions.map((s: any) => this.transformSessionsToMetrics([s])[0]);
        }

        // If no session data in trends, return empty array but log for debugging
        console.warn('Trends API returned no session data, response structure:', data);
        return [];
      } catch (error) {
        console.error('Error fetching sessions:', error);
        throw error;
      }
    });
  }

  /**
   * Transform Analytics API summary response to metrics
   */
  private transformAnalyticsSummaryToMetrics(data: any): SessionMetrics {
    const startedAt = data.started_at ? new Date(data.started_at) : new Date();
    const endedAt = data.ended_at ? new Date(data.ended_at) : new Date();
    const duration = data.duration_seconds ? data.duration_seconds * 1000 : endedAt.getTime() - startedAt.getTime();

    return {
      sessionId: data.session_id,
      projectName: data.project_name || 'Unknown',
      agentType: data.agent_type || 'unknown',
      status: data.status || 'unknown',
      duration,
      startedAt: data.started_at || null,
      completedAt: data.ended_at || null,
      specsCompleted: data.completed_specs || 0,
      specsTotal: data.total_specs || 0,
      errorCount: data.error_count || 0,
      specCompletionRate: data.spec_success_rate || 0,
    };
  }

  /**
   * Transform session data to metrics
   */
  private transformSessionsToMetrics(sessions: any[]): SessionMetrics[] {
    return sessions.map(session => {
      const startedAt = new Date(session.started_at);
      const endedAt = session.ended_at ? new Date(session.ended_at) : new Date();
      const duration = endedAt.getTime() - startedAt.getTime();

      return {
        sessionId: session.id,
        projectName: session.project_name,
        agentType: session.agent_type,
        status: session.status,
        duration,
        startedAt: session.started_at,
        completedAt: session.ended_at,
        specsCompleted: session.completed_specs || 0,
        specsTotal: session.total_specs || 0,
        errorCount: session.error_count || 0,
        specCompletionRate: session.total_specs > 0
          ? (session.completed_specs / session.total_specs) * 100
          : 0,
      };
    });
  }

  /**
   * Fetch error rate metrics grouped by date
   * FIXED: Avoid N+1 query by reusing cached session data
   */
  async fetchErrorRateMetrics(startDate: string, endDate: string): Promise<ErrorRateMetric[]> {
    const cacheKey = `error-metrics-${startDate}-${endDate}`;

    return this.fetchWithCache(cacheKey, async () => {
      try {
        const response = await fetch(
          `${this.baseUrl}/api/query/errors/aggregated?start_date=${startDate}&end_date=${endDate}`
        );
        if (!response.ok) {
          throw new Error(`Failed to fetch error metrics: ${response.statusText}`);
        }

        const data = await response.json();

        // Transform to date-grouped metrics
        const dateMap = new Map<string, ErrorRateMetric>();

        // FIXED: Fetch sessions once and reuse (cached internally)
        const sessions = await this.fetchSessions({ start_date: startDate, end_date: endDate });

        sessions.forEach(session => {
          const date = new Date(session.startedAt).toISOString().split('T')[0];
          if (!dateMap.has(date)) {
            dateMap.set(date, {
              date,
              errorCount: 0,
              sessionCount: 0,
              errorRate: 0,
            });
          }
          const metric = dateMap.get(date)!;
          metric.sessionCount++;
          metric.errorCount += session.errorCount;
        });

        // Calculate error rates
        dateMap.forEach(metric => {
          metric.errorRate = metric.sessionCount > 0
            ? (metric.errorCount / metric.sessionCount)
            : 0;
        });

        return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
      } catch (error) {
        console.error('Error fetching error rate metrics:', error);
        throw error;
      }
    });
  }

  /**
   * Fetch spec completion metrics
   * FIXED: Added caching to avoid repeated queries
   */
  async fetchSpecCompletionMetrics(startDate: string, endDate: string): Promise<SpecCompletionMetric[]> {
    const cacheKey = `spec-metrics-${startDate}-${endDate}`;

    return this.fetchWithCache(cacheKey, async () => {
      try {
        // FIXED: Reuses cached session data due to caching in fetchSessions
        const sessions = await this.fetchSessions({ start_date: startDate, end_date: endDate });

        // Group by spec names from session data
        const specMap = new Map<string, { totalDuration: number; successCount: number; failureCount: number; totalRuns: number }>();

        sessions.forEach(session => {
          // This is a simplified version - in real implementation, you'd fetch spec-level data
          const projectName = session.projectName || 'unknown';
          if (!specMap.has(projectName)) {
            specMap.set(projectName, {
              totalDuration: 0,
              successCount: 0,
              failureCount: 0,
              totalRuns: 0,
            });
          }
          const metric = specMap.get(projectName)!;
          metric.totalDuration += session.duration;
          metric.totalRuns++;
          if (session.status === 'completed') {
            metric.successCount++;
          } else if (session.status === 'failed') {
            metric.failureCount++;
          }
        });

        return Array.from(specMap.entries()).map(([specName, data]) => ({
          specName,
          avgDuration: data.totalRuns > 0 ? data.totalDuration / data.totalRuns : 0,
          successRate: data.totalRuns > 0 ? (data.successCount / data.totalRuns) * 100 : 0,
          failureCount: data.failureCount,
          totalRuns: data.totalRuns,
        }));
      } catch (error) {
        console.error('Error fetching spec completion metrics:', error);
        throw error;
      }
    });
  }

  /**
   * Fetch agent performance metrics
   * FIXED: Added caching to avoid repeated queries
   */
  async fetchAgentPerformanceMetrics(startDate: string, endDate: string): Promise<AgentPerformanceMetric[]> {
    const cacheKey = `agent-metrics-${startDate}-${endDate}`;

    return this.fetchWithCache(cacheKey, async () => {
      try {
        // FIXED: Reuses cached session data due to caching in fetchSessions
        const sessions = await this.fetchSessions({ start_date: startDate, end_date: endDate });

        const agentMap = new Map<string, {
          sessionCount: number;
          totalDuration: number;
          successCount: number;
          errorCount: number;
        }>();

        sessions.forEach(session => {
          const agentType = session.agentType;
          if (!agentMap.has(agentType)) {
            agentMap.set(agentType, {
              sessionCount: 0,
              totalDuration: 0,
              successCount: 0,
              errorCount: 0,
            });
          }
          const metric = agentMap.get(agentType)!;
          metric.sessionCount++;
          metric.totalDuration += session.duration;
          metric.errorCount += session.errorCount;
          if (session.status === 'completed') {
            metric.successCount++;
          }
        });

        return Array.from(agentMap.entries()).map(([agentType, data]) => ({
          agentType: agentType as any,
          sessionCount: data.sessionCount,
          avgDuration: data.sessionCount > 0 ? data.totalDuration / data.sessionCount : 0,
          successRate: data.sessionCount > 0 ? (data.successCount / data.sessionCount) * 100 : 0,
          errorCount: data.errorCount,
        }));
      } catch (error) {
        console.error('Error fetching agent performance metrics:', error);
        throw error;
      }
    });
  }

  /**
   * Generate comprehensive report data
   */
  async generateReportData(startDate: string, endDate: string): Promise<ReportData> {
    try {
      const [sessions, errorMetrics, specMetrics, agentMetrics] = await Promise.all([
        this.fetchSessions({ start_date: startDate, end_date: endDate }),
        this.fetchErrorRateMetrics(startDate, endDate),
        this.fetchSpecCompletionMetrics(startDate, endDate),
        this.fetchAgentPerformanceMetrics(startDate, endDate),
      ]);

      // Calculate summary
      const summary = {
        totalSessions: sessions.length,
        completedSessions: sessions.filter(s => s.status === 'completed').length,
        failedSessions: sessions.filter(s => s.status === 'failed').length,
        cancelledSessions: sessions.filter(s => s.status === 'cancelled').length,
        totalErrors: sessions.reduce((sum, s) => sum + s.errorCount, 0),
        avgSessionDuration: sessions.length > 0
          ? sessions.reduce((sum, s) => sum + s.duration, 0) / sessions.length
          : 0,
      };

      return {
        generatedAt: new Date().toISOString(),
        dateRange: {
          start: startDate,
          end: endDate,
        },
        summary,
        sessionMetrics: sessions,
        errorRateMetrics: errorMetrics,
        specCompletionMetrics: specMetrics,
        agentPerformanceMetrics: agentMetrics,
      };
    } catch (error) {
      console.error('Error generating report data:', error);
      throw error;
    }
  }

  /**
   * Export report as Markdown
   */
  exportAsMarkdown(reportData: ReportData): string {
    const lines: string[] = [];

    // Title
    lines.push('# Dope Dash Analytics Report\n');
    lines.push(`**Generated:** ${new Date(reportData.generatedAt).toLocaleString()}\n`);
    lines.push(`**Date Range:** ${new Date(reportData.dateRange.start).toLocaleDateString()} - ${new Date(reportData.dateRange.end).toLocaleDateString()}\n`);

    // Summary
    lines.push('## Summary\n');
    lines.push('| Metric | Value |');
    lines.push('|--------|-------|');
    lines.push(`| Total Sessions | ${reportData.summary.totalSessions} |`);
    lines.push(`| Completed | ${reportData.summary.completedSessions} |`);
    lines.push(`| Failed | ${reportData.summary.failedSessions} |`);
    lines.push(`| Cancelled | ${reportData.summary.cancelledSessions} |`);
    lines.push(`| Total Errors | ${reportData.summary.totalErrors} |`);
    lines.push(`| Avg Session Duration | ${this.formatDuration(reportData.summary.avgSessionDuration)} |\n`);

    // Session Details
    if (reportData.sessionMetrics.length > 0) {
      lines.push('## Session Details\n');
      lines.push('| Project | Agent | Status | Duration | Specs | Errors |');
      lines.push('|---------|-------|--------|----------|-------|--------|');
      reportData.sessionMetrics.forEach(session => {
        lines.push(`| ${session.projectName} | ${session.agentType} | ${session.status} | ${this.formatDuration(session.duration)} | ${session.specsCompleted}/${session.specsTotal} | ${session.errorCount} |`);
      });
      lines.push('');
    }

    // Error Rate Trends
    if (reportData.errorRateMetrics.length > 0) {
      lines.push('## Error Rate Trends\n');
      lines.push('| Date | Sessions | Errors | Error Rate |');
      lines.push('|------|----------|--------|------------|');
      reportData.errorRateMetrics.forEach(metric => {
        lines.push(`| ${metric.date} | ${metric.sessionCount} | ${metric.errorCount} | ${metric.errorRate.toFixed(2)} |`);
      });
      lines.push('');
    }

    // Spec Completion
    if (reportData.specCompletionMetrics.length > 0) {
      lines.push('## Spec Completion Metrics\n');
      lines.push('| Spec | Avg Duration | Success Rate | Failures | Runs |');
      lines.push('|------|--------------|--------------|----------|------|');
      reportData.specCompletionMetrics.forEach(metric => {
        lines.push(`| ${metric.specName} | ${this.formatDuration(metric.avgDuration)} | ${metric.successRate.toFixed(1)}% | ${metric.failureCount} | ${metric.totalRuns} |`);
      });
      lines.push('');
    }

    // Agent Performance
    if (reportData.agentPerformanceMetrics.length > 0) {
      lines.push('## Agent Performance\n');
      lines.push('| Agent | Sessions | Avg Duration | Success Rate | Errors |');
      lines.push('|-------|----------|--------------|--------------|--------|');
      reportData.agentPerformanceMetrics.forEach(metric => {
        lines.push(`| ${metric.agentType} | ${metric.sessionCount} | ${this.formatDuration(metric.avgDuration)} | ${metric.successRate.toFixed(1)}% | ${metric.errorCount} |`);
      });
      lines.push('');
    }

    return lines.join('\n');
  }

  /**
   * Format duration in milliseconds to human-readable format
   */
  private formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }

  /**
   * Download markdown file
   */
  downloadMarkdown(content: string, filename: string): void {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.md') ? filename : `${filename}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

// Singleton instance
let analyticsServiceInstance: AnalyticsService | null = null;

export const getAnalyticsService = (): AnalyticsService => {
  if (!analyticsServiceInstance) {
    analyticsServiceInstance = new AnalyticsService();
  }
  return analyticsServiceInstance;
};

export default AnalyticsService;
