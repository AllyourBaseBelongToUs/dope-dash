'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { ReportConfig, ReportType, ReportFormat } from '@/types/reports';
import { Calendar, FileText, Settings } from 'lucide-react';

interface ReportGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (config: ReportConfig) => void;
  sessions?: Array<{ id: string; projectName: string }>;
  loading?: boolean;
}

export function ReportGenerationDialog({
  open,
  onOpenChange,
  onGenerate,
  sessions = [],
  loading = false,
}: ReportGenerationDialogProps) {
  const [reportType, setReportType] = useState<ReportType>('session');
  const [format, setFormat] = useState<ReportFormat>('markdown');
  const [title, setTitle] = useState('');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [compareSessions, setCompareSessions] = useState<string[]>([]);

  const handleGenerate = () => {
    const config: ReportConfig = {
      type: reportType,
      format,
      title: title || `${reportType} report`,
      includeCharts,
    };

    if (reportType === 'session' && selectedSessions.length > 0) {
      config.sessionIds = selectedSessions;
    }

    if (reportType === 'comparison' && compareSessions.length >= 2) {
      config.compareSessionIds = compareSessions.slice(0, 5);
    }

    if (dateFrom && dateTo) {
      config.dateFrom = dateFrom;
      config.dateTo = dateTo;
    }

    onGenerate(config);

    // Reset form
    setTitle('');
    setDateFrom('');
    setDateTo('');
    setSelectedSessions([]);
    setCompareSessions([]);
    setIncludeCharts(true);
  };

  const isSessionSelectionRequired = reportType === 'session';
  const isComparisonRequired = reportType === 'comparison';
  const canGenerate =
    title.trim() !== '' &&
    (!isSessionSelectionRequired || selectedSessions.length > 0) &&
    (!isComparisonRequired || compareSessions.length >= 2);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Generate Report
          </DialogTitle>
          <DialogDescription>
            Configure and generate a custom report for your testing sessions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Report Type */}
          <div className="space-y-2">
            <Label htmlFor="report-type">Report Type</Label>
            <Select value={reportType} onValueChange={(value) => setReportType(value as ReportType)}>
              <SelectTrigger id="report-type">
                <SelectValue placeholder="Select report type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="session">Session Report</SelectItem>
                <SelectItem value="trends">Trends Analysis</SelectItem>
                <SelectItem value="comparison">Session Comparison</SelectItem>
                <SelectItem value="error_analysis">Error Analysis</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Report Title</Label>
            <Input
              id="title"
              placeholder="My Test Report"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Format */}
          <div className="space-y-2">
            <Label htmlFor="format">Format</Label>
            <Select value={format} onValueChange={(value) => setFormat(value as ReportFormat)}>
              <SelectTrigger id="format">
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="markdown">Markdown</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="json">JSON</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Date Range */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Date Range (Optional)
            </Label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="date-from" className="text-sm text-slate-400">
                  From
                </Label>
                <Input
                  id="date-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="date-to" className="text-sm text-slate-400">
                  To
                </Label>
                <Input
                  id="date-to"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Session Selection */}
          {isSessionSelectionRequired && sessions.length > 0 && (
            <div className="space-y-2">
              <Label htmlFor="sessions">Select Sessions</Label>
              <div className="border rounded-md p-3 max-h-40 overflow-y-auto bg-slate-950/50">
                {sessions.length === 0 ? (
                  <p className="text-sm text-slate-500">No sessions available</p>
                ) : (
                  sessions.map((session) => (
                    <div key={session.id} className="flex items-center gap-2 py-2">
                      <input
                        type="checkbox"
                        id={`session-${session.id}`}
                        checked={selectedSessions.includes(session.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedSessions([...selectedSessions, session.id]);
                          } else {
                            setSelectedSessions(selectedSessions.filter((id) => id !== session.id));
                          }
                        }}
                        className="rounded"
                      />
                      <label
                        htmlFor={`session-${session.id}`}
                        className="text-sm flex-1 cursor-pointer"
                      >
                        {session.projectName}
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Comparison Sessions */}
          {isComparisonRequired && sessions.length > 0 && (
            <div className="space-y-2">
              <Label htmlFor="compare-sessions">
                Select Sessions to Compare (2-5)
              </Label>
              <div className="border rounded-md p-3 max-h-40 overflow-y-auto bg-slate-950/50">
                {sessions.length === 0 ? (
                  <p className="text-sm text-slate-500">No sessions available</p>
                ) : (
                  sessions.map((session) => (
                    <div key={session.id} className="flex items-center gap-2 py-2">
                      <input
                        type="checkbox"
                        id={`compare-${session.id}`}
                        checked={compareSessions.includes(session.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            if (compareSessions.length < 5) {
                              setCompareSessions([...compareSessions, session.id]);
                            }
                          } else {
                            setCompareSessions(compareSessions.filter((id) => id !== session.id));
                          }
                        }}
                        disabled={
                          !compareSessions.includes(session.id) && compareSessions.length >= 5
                        }
                        className="rounded"
                      />
                      <label
                        htmlFor={`compare-${session.id}`}
                        className="text-sm flex-1 cursor-pointer"
                      >
                        {session.projectName}
                      </label>
                    </div>
                  ))
                )}
              </div>
              <p className="text-xs text-slate-500">
                {compareSessions.length}/5 sessions selected
              </p>
            </div>
          )}

          {/* Include Charts */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="include-charts" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Include Charts
              </Label>
              <p className="text-xs text-slate-500">
                Add visualizations to the report
              </p>
            </div>
            <Switch
              id="include-charts"
              checked={includeCharts}
              onCheckedChange={setIncludeCharts}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={!canGenerate || loading}>
            {loading ? 'Generating...' : 'Generate Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
