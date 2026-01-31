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
import { ReportScheduleConfig, ReportType, ReportFormat, ReportSchedule } from '@/types/reports';
import { Clock, Calendar, Settings } from 'lucide-react';

interface ScheduleSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (config: ReportScheduleConfig) => void;
  currentConfig?: ReportScheduleConfig;
  loading?: boolean;
}

const DAYS_OF_WEEK = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];

export function ScheduleSettingsDialog({
  open,
  onOpenChange,
  onSave,
  currentConfig,
  loading = false,
}: ScheduleSettingsDialogProps) {
  const [enabled, setEnabled] = useState(currentConfig?.enabled ?? false);
  const [frequency, setFrequency] = useState<ReportSchedule>(
    currentConfig?.frequency ?? 'daily'
  );
  const [time, setTime] = useState(currentConfig?.time ?? '09:00');
  const [dayOfWeek, setDayOfWeek] = useState(currentConfig?.dayOfWeek ?? 1); // Monday
  const [dayOfMonth, setDayOfMonth] = useState(currentConfig?.dayOfMonth ?? 1);
  const [format, setFormat] = useState<ReportFormat>(currentConfig?.format ?? 'markdown');
  const [reportTypes, setReportTypes] = useState<ReportType[]>(
    currentConfig?.reportTypes ?? ['trends']
  );
  const [retentionDays, setRetentionDays] = useState(currentConfig?.retentionDays ?? 30);

  const handleSave = () => {
    const config: ReportScheduleConfig = {
      enabled,
      frequency,
      reportTypes,
      format,
      retentionDays,
    };

    if (enabled) {
      if (frequency === 'daily' || frequency === 'weekly') {
        config.time = time;
      }
      if (frequency === 'weekly') {
        config.dayOfWeek = dayOfWeek;
      }
      if (frequency === 'monthly') {
        config.dayOfMonth = dayOfMonth;
      }
    }

    onSave(config);
    onOpenChange(false);
  };

  const toggleReportType = (type: ReportType) => {
    if (reportTypes.includes(type)) {
      // Don't allow deselecting if it's the only one
      if (reportTypes.length > 1) {
        setReportTypes(reportTypes.filter((t) => t !== type));
      }
    } else {
      setReportTypes([...reportTypes, type]);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Report Schedule Settings
          </DialogTitle>
          <DialogDescription>
            Configure automatic report generation schedules.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Enable Schedule */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="enabled" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Enable Scheduled Reports
              </Label>
              <p className="text-xs text-slate-500">
                Automatically generate reports on a schedule
              </p>
            </div>
            <Switch id="enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {enabled && (
            <>
              {/* Frequency */}
              <div className="space-y-2">
                <Label htmlFor="frequency">Frequency</Label>
                <Select
                  value={frequency}
                  onValueChange={(value) => setFrequency(value as ReportSchedule)}
                >
                  <SelectTrigger id="frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Time (for daily/weekly) */}
              {(frequency === 'daily' || frequency === 'weekly') && (
                <div className="space-y-2">
                  <Label htmlFor="time">Time</Label>
                  <Input
                    id="time"
                    type="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                  />
                </div>
              )}

              {/* Day of Week (for weekly) */}
              {frequency === 'weekly' && (
                <div className="space-y-2">
                  <Label htmlFor="day-of-week">Day of Week</Label>
                  <Select
                    value={dayOfWeek.toString()}
                    onValueChange={(value) => setDayOfWeek(parseInt(value))}
                  >
                    <SelectTrigger id="day-of-week">
                      <SelectValue placeholder="Select day" />
                    </SelectTrigger>
                    <SelectContent>
                      {DAYS_OF_WEEK.map((day, index) => (
                        <SelectItem key={day} value={index.toString()}>
                          {day}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Day of Month (for monthly) */}
              {frequency === 'monthly' && (
                <div className="space-y-2">
                  <Label htmlFor="day-of-month">Day of Month</Label>
                  <Select
                    value={dayOfMonth.toString()}
                    onValueChange={(value) => setDayOfMonth(parseInt(value))}
                  >
                    <SelectTrigger id="day-of-month">
                      <SelectValue placeholder="Select day" />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                        <SelectItem key={day} value={day.toString()}>
                          {day}{day === 1 ? 'st' : day === 2 ? 'nd' : day === 3 ? 'rd' : 'th'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Report Types */}
              <div className="space-y-2">
                <Label>Report Types</Label>
                <div className="space-y-2">
                  {([
                    'trends',
                    'error_analysis',
                    'session',
                    'comparison',
                  ] as ReportType[]).map((type) => (
                    <div key={type} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`report-type-${type}`}
                        checked={reportTypes.includes(type)}
                        onChange={() => toggleReportType(type)}
                        disabled={
                          !reportTypes.includes(type) && reportTypes.length >= 3
                        }
                        className="rounded"
                      />
                      <label
                        htmlFor={`report-type-${type}`}
                        className="text-sm cursor-pointer capitalize"
                      >
                        {type.replace('_', ' ')}
                      </label>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-500">
                  Select up to 3 report types to include
                </p>
              </div>

              {/* Format */}
              <div className="space-y-2">
                <Label htmlFor="format">Default Format</Label>
                <Select
                  value={format}
                  onValueChange={(value) => setFormat(value as ReportFormat)}
                >
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

              {/* Retention */}
              <div className="space-y-2">
                <Label htmlFor="retention">Retention Period (Days)</Label>
                <Input
                  id="retention"
                  type="number"
                  min={1}
                  max={365}
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(parseInt(e.target.value) || 30)}
                />
                <p className="text-xs text-slate-500">
                  Reports older than this will be automatically deleted
                </p>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? 'Saving...' : 'Save Settings'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
