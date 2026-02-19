'use client';

import { useState, useEffect } from 'react';
import { useReportStore } from '@/store/reportStore';
import { useDashboardStore } from '@/store/dashboardStore';
import { Button } from '@/components/ui/button';
import {
  FileText,
  Download,
  Calendar,
  Trash2,
  RefreshCw,
  BarChart3,
  TrendingUp,
  GitCompare,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  FileDown,
  Settings,
  Plus,
} from 'lucide-react';
import type { ReportType, ReportFormat, ReportSchedule } from '@/types/reports';
import { ReportGenerationDialog } from '@/components/reports/dialogs/ReportGenerationDialog';
import { ScheduleSettingsDialog } from '@/components/reports/dialogs/ScheduleSettingsDialog';
import { ScheduleCard } from '@/components/reports/ScheduleCard';
import { ReportHistory } from '@/components/reports/ReportHistory';
import { ReportViewer } from '@/components/reports/ReportViewer';
import {
  SessionDurationChart,
  EventBreakdownChart,
  TrendChart,
  ComparisonChart,
} from '@/components/reports/charts';
import { reportService } from '@/services/reportService';
import { reportScheduleService } from '@/services/reportScheduleService';
import { format } from 'date-fns';

export default function ReportsPage() {
  const {
    reports,
    selectedReport,
    isGenerating,
    templates,
    scheduleConfig,
    setReports,
    setSelectedReport,
    generateReport,
    downloadReport,
    deleteReport,
    updateScheduleConfig,
  } = useReportStore();

  const { sessions } = useDashboardStore();
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
  const [schedules, setSchedules] = useState<any[]>([]);

  // Load reports and schedules on mount
  useEffect(() => {
    loadReports();
    loadSchedules();
  }, []);

  const loadReports = async () => {
    try {
      const data = await reportService.getReports();
      setReports(data);
    } catch (error) {
      console.error('Failed to load reports:', error);
    }
  };

  const loadSchedules = async () => {
    try {
      const data = await reportScheduleService.getSchedules();
      setSchedules(data);
    } catch (error) {
      console.error('Failed to load schedules:', error);
    }
  };

  const handleGenerateReport = async (config: any) => {
    try {
      await generateReport(config);
      setShowGenerateDialog(false);
      await loadReports();
    } catch (error) {
      console.error('Failed to generate report:', error);
    }
  };

  const handleDownload = async (reportId: string) => {
    try {
      await downloadReport(reportId);
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const handleDelete = async (reportId: string) => {
    try {
      await deleteReport(reportId);
      await reportService.deleteReport(reportId);
      await loadReports();
      if (selectedReport?.id === reportId) {
        setSelectedReport(null);
      }
    } catch (error) {
      console.error('Failed to delete report:', error);
    }
  };

  const handleScheduleSave = async (config: any) => {
    try {
      updateScheduleConfig(config);
      await loadSchedules();
      setShowScheduleDialog(false);
    } catch (error) {
      console.error('Failed to save schedule:', error);
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    try {
      await reportScheduleService.deleteSchedule(scheduleId);
      await loadSchedules();
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  };

  const handleToggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      await reportScheduleService.updateSchedule(scheduleId, { enabled });
      await loadSchedules();
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'generating':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTemplateIcon = (type: ReportType) => {
    switch (type) {
      case 'session':
        return <FileText className="h-4 w-4" />;
      case 'trends':
        return <TrendingUp className="h-4 w-4" />;
      case 'comparison':
        return <GitCompare className="h-4 w-4" />;
      case 'error_analysis':
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <BarChart3 className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Reports</h1>
                <p className="text-xs text-muted-foreground">Analytics & Report Generation</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowScheduleDialog(true)}
              >
                <Settings className="h-4 w-4 mr-2" />
                Schedule Settings
              </Button>
              <Button
                size="sm"
                onClick={() => setShowGenerateDialog(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Report
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        {/* Active Schedules */}
        {schedules.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4">Active Schedules</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {schedules.map((schedule) => (
                <ScheduleCard
                  key={schedule.id}
                  schedule={schedule}
                  onEdit={() => setShowScheduleDialog(true)}
                  onDelete={() => handleDeleteSchedule(schedule.id)}
                  onToggle={(enabled) => handleToggleSchedule(schedule.id, enabled)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Quick Generate */}
        <div className="mb-6 p-4 border border-border rounded-lg bg-card">
          <h3 className="text-lg font-semibold mb-4">Quick Generate</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {templates.slice(0, 4).map((template) => (
              <Button
                key={template.id}
                variant="outline"
                className="h-auto py-4 flex flex-col items-center gap-2"
                onClick={() => {
                  const config = {
                    ...template.config,
                    format: template.defaultFormat,
                    title: template.name,
                    type: template.type,
                  };
                  handleGenerateReport(config);
                }}
                disabled={isGenerating}
              >
                {getTemplateIcon(template.type)}
                <span className="text-sm">{template.name}</span>
                <span className="text-xs text-muted-foreground">{template.defaultFormat}</span>
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Report History */}
          <div className="lg:col-span-1">
            <ReportHistory
              reports={reports}
              selectedReport={selectedReport}
              onSelectReport={setSelectedReport}
              onDownload={handleDownload}
              onDelete={handleDelete}
              isGenerating={isGenerating}
            />
          </div>

          {/* Report Details / Charts */}
          <div className="lg:col-span-2">
            {selectedReport ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{selectedReport.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {format(new Date(selectedReport.createdAt), 'MMM dd, yyyy HH:mm')}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 mr-4">
                      {getStatusIcon(selectedReport.status)}
                      <span className="text-sm capitalize">{selectedReport.status}</span>
                    </div>
                    <Button
                      onClick={() => handleDownload(selectedReport.id)}
                      disabled={selectedReport.status !== 'completed'}
                    >
                      <FileDown className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>
                </div>

                {selectedReport.status === 'generating' && (
                  <div className="border border-dashed border-border rounded-lg p-8 text-center">
                    <RefreshCw className="h-12 w-12 text-primary mx-auto mb-4 animate-spin" />
                    <p className="text-muted-foreground">Generating report...</p>
                  </div>
                )}

                {selectedReport.status === 'failed' && (
                  <div className="border border-red-500/50 bg-red-500/10 rounded-lg p-4">
                    <p className="text-red-500">{selectedReport.error || 'Report generation failed'}</p>
                  </div>
                )}

                {selectedReport.status === 'completed' && selectedReport.data && (
                  <div className="space-y-6">
                    {selectedReport.data.sessions && selectedReport.data.sessions.length > 0 && (
                      <>
                        <div className="border border-border rounded-lg p-4 bg-card">
                          <h4 className="font-medium mb-4">Session Duration</h4>
                          <SessionDurationChart sessions={selectedReport.data.sessions} />
                        </div>
                        <div className="border border-border rounded-lg p-4 bg-card">
                          <h4 className="font-medium mb-4">Event Breakdown</h4>
                          <EventBreakdownChart
                            data={Object.entries(
                              selectedReport.data.sessions.reduce((acc: Record<string, number>, session: any) => {
                                Object.entries(session.eventBreakdown || {}).forEach(([type, count]) => {
                                  acc[type] = (acc[type] || 0) + (count as number);
                                });
                                return acc;
                              }, {})
                            ).map(([eventType, count]) => ({ eventType, count: count as number }))}
                          />
                        </div>
                      </>
                    )}

                    {selectedReport.data.trends && (
                      <>
                        <div className="border border-border rounded-lg p-4 bg-card">
                          <h4 className="font-medium mb-4">Session Trends</h4>
                          <TrendChart type="sessions" data={selectedReport.data.trends.sessionTrend || []} />
                        </div>
                        <div className="border border-border rounded-lg p-4 bg-card">
                          <h4 className="font-medium mb-4">Spec Trends</h4>
                          <TrendChart type="specs" data={selectedReport.data.trends.specTrend || []} />
                        </div>
                        <div className="border border-border rounded-lg p-4 bg-card">
                          <h4 className="font-medium mb-4">Error Trends</h4>
                          <TrendChart type="errors" data={selectedReport.data.trends.errorTrend || []} />
                        </div>
                      </>
                    )}

                    {selectedReport.data.comparison && (
                      <div className="border border-border rounded-lg p-4 bg-card">
                        <h4 className="font-medium mb-4">Session Comparison</h4>
                        <ComparisonChart sessions={selectedReport.data.comparison.sessions} />
                      </div>
                    )}

                    {selectedReport.data.errorAnalysis && (
                      <div className="border border-border rounded-lg p-4 bg-card">
                        <h4 className="font-medium mb-4">Error Summary</h4>
                        <div className="space-y-2">
                          <p className="text-sm">
                            Total Errors:{' '}
                            <span className="font-bold">
                              {selectedReport.data.errorAnalysis.totalErrors || 0}
                            </span>
                          </p>
                          <p className="text-sm">
                            Unique Error Types:{' '}
                            <span className="font-bold">
                              {Object.keys(selectedReport.data.errorAnalysis.errorFrequency || {}).length || 0}
                            </span>
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="border border-dashed border-border rounded-lg p-8 text-center">
                <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Select a report to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Dialogs */}
      <ReportGenerationDialog
        open={showGenerateDialog}
        onOpenChange={setShowGenerateDialog}
        onGenerate={handleGenerateReport}
        sessions={sessions}
        loading={isGenerating}
      />

      <ScheduleSettingsDialog
        open={showScheduleDialog}
        onOpenChange={setShowScheduleDialog}
        onSave={handleScheduleSave}
        currentConfig={scheduleConfig}
      />
    </main>
  );
}
