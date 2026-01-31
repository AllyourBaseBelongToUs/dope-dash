import type {
  Report,
  ReportConfig,
  ReportFormat,
  ReportType,
} from '@/types/reports';

/**
 * Report Service
 * Handles report generation, retrieval, download, and deletion via backend API.
 */
class ReportService {
  private baseUrl: string = '';

  constructor() {
    if (typeof window !== 'undefined') {
      this.baseUrl = this.getApiBaseUrl();
    }
  }

  /**
   * Get the API base URL from environment config or fallback
   */
  private getApiBaseUrl(): string {
    // Try to get from environment config
    const envConfig = localStorage.getItem('dope-dash-env-config');
    if (envConfig) {
      try {
        const config = JSON.parse(envConfig);
        return config.apiUrl || this.getDefaultApiUrl();
      } catch (e) {
        console.warn('Failed to parse env config:', e);
      }
    }
    return this.getDefaultApiUrl();
  }

  /**
   * Get default API URL based on current environment
   */
  private getDefaultApiUrl(): string {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
      }
    }
    return 'http://localhost:8000';
  }

  /**
   * Generate a new report via backend API
   */
  async generateReport(config: ReportConfig): Promise<Report> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: config.type,
          format: config.format,
          title: config.title,
          includeCharts: config.includeCharts ?? true,
          sessionIds: config.sessionIds,
          compareSessionIds: config.compareSessionIds,
          dateRange: config.dateRange,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to generate report: ${errorData.detail || response.statusText}`);
      }

      const data = await response.json();
      return this.transformToReport(data);
    } catch (error) {
      console.error('Error generating report:', error);
      throw error;
    }
  }

  /**
   * Get report history from backend API
   */
  async getReports(limit: number = 50, offset: number = 0): Promise<Report[]> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      const response = await fetch(`${this.baseUrl}/api/reports?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch reports: ${response.statusText}`);
      }

      const data = await response.json();
      return data.reports.map((r: any) => this.transformToReport(r));
    } catch (error) {
      console.error('Error fetching reports:', error);
      throw error;
    }
  }

  /**
   * Download a report from backend API
   */
  async downloadReport(reportId: string): Promise<void> {
    try {
      // Direct download via browser
      const link = document.createElement('a');
      link.href = `${this.baseUrl}/api/reports/download/${reportId}`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error downloading report:', error);
      throw error;
    }
  }

  /**
   * Delete a report via backend API
   */
  async deleteReport(reportId: string): Promise<{ status: string; reportId: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/${reportId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to delete report: ${errorData.detail || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting report:', error);
      throw error;
    }
  }

  /**
   * Regenerate a report
   */
  async regenerateReport(reportId: string): Promise<Partial<Report>> {
    // For now, return a placeholder since the backend doesn't support regeneration
    return {
      status: 'generating',
    };
  }

  /**
   * Transform API response to Report type
   */
  private transformToReport(data: any): Report {
    return {
      id: data.id,
      title: data.title || '',
      type: data.type as ReportType,
      format: data.format as ReportFormat,
      status: data.status || 'completed',
      config: data.config || {},
      data: data.data,
      filePath: data.filePath,
      fileSize: data.fileSize,
      createdAt: data.createdAt || new Date().toISOString(),
      completedAt: data.completedAt || data.createdAt,
      error: data.error,
      scheduled: data.scheduled || false,
      schedule: data.schedule,
      nextRunAt: data.nextRunAt,
    };
  }
}

// Singleton instance
let reportServiceInstance: ReportService | null = null;

export const getReportService = (): ReportService => {
  if (!reportServiceInstance) {
    reportServiceInstance = new ReportService();
  }
  return reportServiceInstance;
};

export const reportService = getReportService();
export default ReportService;
