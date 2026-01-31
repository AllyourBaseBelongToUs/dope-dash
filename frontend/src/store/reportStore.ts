import { create } from 'zustand';
import type { Report, ReportConfig, ReportFormat, ReportScheduleConfig, ReportTemplate } from '@/types/reports';
import { reportService } from '@/services/reportService';

interface ReportStore {
  reports: Report[];
  selectedReport: Report | null;
  isGenerating: boolean;
  scheduleConfig: ReportScheduleConfig;
  templates: ReportTemplate[];

  // Actions
  setReports: (reports: Report[]) => void;
  setSelectedReport: (report: Report | null) => void;
  addReport: (report: Report) => void;
  updateReport: (reportId: string, updates: Partial<Report>) => void;
  deleteReport: (reportId: string) => void;
  clearReports: () => void;

  // Generation
  generateReport: (config: ReportConfig) => Promise<Report>;
  downloadReport: (reportId: string) => Promise<void>;
  regenerateReport: (reportId: string) => Promise<void>;
  cancelGeneration: (reportId: string) => void;

  // Scheduling
  setScheduleConfig: (config: ReportScheduleConfig) => void;
  updateScheduleConfig: (config: Partial<ReportScheduleConfig>) => void;
  updateScheduleFrequency: (frequency: ReportScheduleConfig['frequency']) => void;
  updateScheduleRetention: (days: number) => void;
  toggleScheduleEnabled: () => void;

  // Templates
  setTemplates: (templates: ReportTemplate[]) => void;
  createFromTemplate: (templateId: string, overrides?: Partial<ReportConfig>) => Promise<Report>;

  // Cleanup
  cleanupOldReports: (retentionDays: number) => void;
}

const DEFAULT_SCHEDULE_CONFIG: ReportScheduleConfig = {
  enabled: false,
  frequency: 'none',
  reportTypes: ['session', 'trends'],
  format: 'pdf',
  retentionDays: 30,
};

const DEFAULT_TEMPLATES: ReportTemplate[] = [
  {
    id: 'session-summary',
    name: 'Session Summary',
    description: 'Generate a summary report for a single session',
    type: 'session',
    defaultFormat: 'markdown',
    config: {
      type: 'session',
      format: 'markdown',
      title: 'Session Summary Report',
      includeCharts: true,
    },
  },
  {
    id: 'weekly-trends',
    name: 'Weekly Trends',
    description: 'Analyze trends across multiple sessions over time',
    type: 'trends',
    defaultFormat: 'pdf',
    config: {
      type: 'trends',
      format: 'pdf',
      title: 'Weekly Trends Report',
      includeCharts: true,
      dateRangeObject: {
        from: '',
        to: '',
      },
    },
  },
  {
    id: 'comparison-report',
    name: 'Session Comparison',
    description: 'Compare multiple sessions side by side',
    type: 'comparison',
    defaultFormat: 'pdf',
    config: {
      type: 'comparison',
      format: 'pdf',
      title: 'Session Comparison Report',
      includeCharts: true,
      compareSessionIds: [],
    },
  },
  {
    id: 'error-analysis',
    name: 'Error Analysis',
    description: 'Detailed analysis of errors across sessions',
    type: 'error_analysis',
    defaultFormat: 'markdown',
    config: {
      type: 'error_analysis',
      format: 'markdown',
      title: 'Error Analysis Report',
      includeCharts: true,
    },
  },
];

export const useReportStore = create<ReportStore>((set, get) => ({
  reports: [],
  selectedReport: null,
  isGenerating: false,
  scheduleConfig: DEFAULT_SCHEDULE_CONFIG,
  templates: DEFAULT_TEMPLATES,

  setReports: (reports) => set({ reports }),

  setSelectedReport: (report) => set({ selectedReport: report }),

  addReport: (report) => set((state) => ({
    reports: [report, ...state.reports],
  })),

  updateReport: (reportId, updates) => set((state) => ({
    reports: state.reports.map((r) =>
      r.id === reportId ? { ...r, ...updates } : r
    ),
    selectedReport:
      state.selectedReport?.id === reportId
        ? { ...state.selectedReport, ...updates }
        : state.selectedReport,
  })),

  deleteReport: (reportId) => set((state) => ({
    reports: state.reports.filter((r) => r.id !== reportId),
    selectedReport:
      state.selectedReport?.id === reportId ? null : state.selectedReport,
  })),

  clearReports: () => set({ reports: [], selectedReport: null }),

  generateReport: async (config) => {
    set({ isGenerating: true });
    try {
      const report = await reportService.generateReport(config);
      get().addReport(report);
      return report;
    } finally {
      set({ isGenerating: false });
    }
  },

  downloadReport: async (reportId) => {
    const report = get().reports.find((r) => r.id === reportId);
    if (!report) {
      throw new Error('Report not found');
    }
    await reportService.downloadReport(reportId);
  },

  regenerateReport: async (reportId) => {
    const report = get().reports.find((r) => r.id === reportId);
    if (!report) {
      throw new Error('Report not found');
    }
    set({ isGenerating: true });
    try {
      get().updateReport(reportId, { status: 'generating' });
      const regenerated = await reportService.regenerateReport(reportId);
      get().updateReport(reportId, regenerated);
    } finally {
      set({ isGenerating: false });
    }
  },

  cancelGeneration: (reportId) => {
    const report = get().reports.find((r) => r.id === reportId);
    if (report?.status === 'generating') {
      get().updateReport(reportId, {
        status: 'failed',
        error: 'Report generation cancelled by user',
      });
    }
  },

  setScheduleConfig: (config) => set({ scheduleConfig: config }),

  updateScheduleConfig: (config) => set((state) => ({
    scheduleConfig: { ...state.scheduleConfig, ...config },
  })),

  updateScheduleFrequency: (frequency) => set((state) => ({
    scheduleConfig: { ...state.scheduleConfig, frequency },
  })),

  updateScheduleRetention: (days) => set((state) => ({
    scheduleConfig: { ...state.scheduleConfig, retentionDays: days },
  })),

  toggleScheduleEnabled: () => set((state) => ({
    scheduleConfig: {
      ...state.scheduleConfig,
      enabled: !state.scheduleConfig.enabled,
    },
  })),

  setTemplates: (templates) => set({ templates }),

  createFromTemplate: async (templateId, overrides) => {
    const template = get().templates.find((t) => t.id === templateId);
    if (!template) {
      throw new Error('Template not found');
    }

    const config: ReportConfig = {
      ...template.config,
      ...overrides,
      type: template.type,
      format: overrides?.format || template.defaultFormat,
    } as ReportConfig;

    return get().generateReport(config);
  },

  cleanupOldReports: (retentionDays) => {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    const currentReports = get().reports;
    const filteredReports = currentReports.filter((r) => {
      const reportDate = new Date(r.createdAt);
      return reportDate > cutoffDate;
    });

    if (filteredReports.length < currentReports.length) {
      set({ reports: filteredReports });
      console.info(`Cleaned up ${currentReports.length - filteredReports.length} old reports`);
    }
  },
}));
