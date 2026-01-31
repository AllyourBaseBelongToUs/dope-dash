'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useReportStore } from '@/store/reportStore';
import { useDashboardStore } from '@/store/dashboardStore';
import type { ReportFormat, ReportType } from '@/types/reports';
import { FileText, Download, Calendar, Settings } from 'lucide-react';

/**
 * Report Generator Component
 * Dialog for generating new reports with various options
 */

interface ReportGeneratorProps {
  trigger?: React.ReactNode;
}

export function ReportGenerator({ trigger }: ReportGeneratorProps) {
  const [open, setOpen] = useState(false);
  const [reportType, setReportType] = useState<ReportType>('session');
  const [format, setFormat] = useState<ReportFormat>('pdf');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [title, setTitle] = useState('');
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);

  const { generateReport, isGenerating, templates } = useReportStore();
  const { sessions } = useDashboardStore();

  const handleGenerate = async () => {
    const config = {
      type: reportType,
      format,
      title: title || `${reportType.charAt(0).toUpperCase() + reportType.slice(1)} Report`,
      includeCharts,
      sessionIds: selectedSessions.length > 0 ? selectedSessions : undefined,
    };

    try {
      await generateReport(config);
      setOpen(false);
      // Reset form
      setTitle('');
      setSelectedSessions([]);
      setIncludeCharts(true);
    } catch (error) {
      console.error('Failed to generate report:', error);
    }
  };

  const handleTemplateSelect = async (templateId: string) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setReportType(template.type);
      setFormat(template.defaultFormat);
      setTitle(template.name);
    }
  };

  const handleToggleSession = (sessionId: string) => {
    setSelectedSessions((prev) =>
      prev.includes(sessionId)
        ? prev.filter((id) => id !== sessionId)
        : [...prev, sessionId]
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <FileText className="mr-2 h-4 w-4" />
            Generate Report
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Generate Report</DialogTitle>
          <DialogDescription>
            Create a detailed report from your analytics data. Choose the type, format, and
            customize the content.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Quick Templates */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Quick Templates</Label>
            <div className="grid grid-cols-2 gap-2">
              {templates.map((template) => (
                <Button
                  key={template.id}
                  variant="outline"
                  size="sm"
                  className="justify-start"
                  onClick={() => handleTemplateSelect(template.id)}
                >
                  {template.name}
                </Button>
              ))}
            </div>
          </div>

          {/* Report Type */}
          <div className="space-y-2">
            <Label htmlFor="report-type">Report Type</Label>
            <Select value={reportType} onValueChange={(v) => setReportType(v as ReportType)}>
              <SelectTrigger id="report-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="session">Session Summary</SelectItem>
                <SelectItem value="trends">Trends Analysis</SelectItem>
                <SelectItem value="comparison">Session Comparison</SelectItem>
                <SelectItem value="error_analysis">Error Analysis</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Format */}
          <div className="space-y-2">
            <Label htmlFor="format">Format</Label>
            <Select value={format} onValueChange={(v) => setFormat(v as ReportFormat)}>
              <SelectTrigger id="format">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="markdown">Markdown</SelectItem>
                <SelectItem value="json">JSON</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter report title..."
            />
          </div>

          {/* Include Charts */}
          <div className="flex items-center justify-between">
            <Label htmlFor="charts">Include Charts</Label>
            <Switch
              id="charts"
              checked={includeCharts}
              onCheckedChange={setIncludeCharts}
            />
          </div>

          {/* Session Selection (for session/comparison reports) */}
          {(reportType === 'session' || reportType === 'comparison') && (
            <div className="space-y-2">
              <Label>Select Sessions</Label>
              <div className="max-h-40 overflow-y-auto border rounded-md p-2">
                {sessions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No sessions available</p>
                ) : (
                  sessions.slice(0, 10).map((session) => (
                    <div key={session.id} className="flex items-center space-x-2 py-1">
                      <input
                        type="checkbox"
                        id={`session-${session.id}`}
                        checked={selectedSessions.includes(session.id)}
                        onChange={() => handleToggleSession(session.id)}
                        className="h-4 w-4"
                      />
                      <label
                        htmlFor={`session-${session.id}`}
                        className="text-sm cursor-pointer flex-1 truncate"
                      >
                        {session.projectName} ({session.status})
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={isGenerating}>
            {isGenerating ? (
              <>Generating...</>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Generate Report
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
