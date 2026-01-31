import type {
  ReportScheduleConfig,
  ReportType,
  ReportFormat,
} from '@/types/reports';

interface ReportSchedule {
  id: string;
  name: string;
  enabled: boolean;
  frequency: ReportSchedule;
  reportTypes: ReportType[];
  format: ReportFormat;
  retentionDays: number;
  config: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  lastRunAt?: string;
  nextRunAt?: string;
}

/**
 * Report Schedule Service
 * Handles report scheduling configuration and management via backend API.
 */
class ReportScheduleService {
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
   * Get all schedules
   */
  async getSchedules(): Promise<ReportSchedule[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/schedules`);

      if (!response.ok) {
        throw new Error(`Failed to fetch schedules: ${response.statusText}`);
      }

      const data = await response.json();
      return data.schedules.map((s: any) => this.transformToSchedule(s));
    } catch (error) {
      console.error('Error fetching schedules:', error);
      throw error;
    }
  }

  /**
   * Create a new schedule
   */
  async createSchedule(config: ReportScheduleConfig & { name: string }): Promise<ReportSchedule> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/schedules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to create schedule: ${errorData.detail || response.statusText}`);
      }

      const data = await response.json();
      return this.transformToSchedule(data);
    } catch (error) {
      console.error('Error creating schedule:', error);
      throw error;
    }
  }

  /**
   * Update schedule configuration
   */
  async updateSchedule(
    id: string,
    config: Partial<ReportScheduleConfig>
  ): Promise<ReportSchedule> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/schedules/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to update schedule: ${errorData.detail || response.statusText}`);
      }

      const data = await response.json();
      return this.transformToSchedule(data);
    } catch (error) {
      console.error('Error updating schedule:', error);
      throw error;
    }
  }

  /**
   * Delete schedule
   */
  async deleteSchedule(id: string): Promise<{ status: string; scheduleId: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/schedules/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to delete schedule: ${errorData.detail || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting schedule:', error);
      throw error;
    }
  }

  /**
   * Test schedule by running it immediately
   */
  async testSchedule(scheduleId: string): Promise<{
    scheduleId: string;
    scheduleName: string;
    generatedReports: any[];
    testRunAt: string;
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/schedules/${scheduleId}/test`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to test schedule: ${errorData.detail || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error testing schedule:', error);
      throw error;
    }
  }

  /**
   * Transform API response to ReportSchedule type
   */
  private transformToSchedule(data: any): ReportSchedule {
    return {
      id: data.id,
      name: data.name,
      enabled: data.enabled,
      frequency: data.frequency,
      reportTypes: data.reportTypes || [],
      format: data.format,
      retentionDays: data.retentionDays,
      config: data.config || {},
      createdAt: data.createdAt,
      updatedAt: data.updatedAt,
      lastRunAt: data.lastRunAt,
      nextRunAt: data.nextRunAt,
    };
  }

  /**
   * Clean up old reports
   */
  async cleanupReports(retentionDays: number = 30): Promise<{
    status: string;
    deletedCount: number;
    retentionDays: number;
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/reports/cleanup?retentionDays=${retentionDays}`,
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`Failed to cleanup reports: ${errorData.detail || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error cleaning up reports:', error);
      throw error;
    }
  }
}

// Singleton instance
let scheduleServiceInstance: ReportScheduleService | null = null;

export const getReportScheduleService = (): ReportScheduleService => {
  if (!scheduleServiceInstance) {
    scheduleServiceInstance = new ReportScheduleService();
  }
  return scheduleServiceInstance;
};

export const reportScheduleService = getReportScheduleService();
export default ReportScheduleService;
