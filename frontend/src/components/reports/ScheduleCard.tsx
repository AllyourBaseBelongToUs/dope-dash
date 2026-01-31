'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ReportScheduleConfig, ReportSchedule, ReportType, ReportFormat } from '@/types/reports';
import {
  Clock,
  Calendar,
  Edit,
  Trash2,
  CheckCircle2,
  XCircle,
  Settings,
} from 'lucide-react';

interface ScheduleCardProps {
  schedule: {
    id: string;
    name: string;
    enabled: boolean;
    frequency: ReportSchedule;
    reportTypes: ReportType[];
    format: ReportFormat;
    retentionDays: number;
    nextRunAt?: string;
    lastRunAt?: string;
  };
  onEdit?: () => void;
  onDelete?: () => void;
  onToggle?: (enabled: boolean) => void;
}

const getFrequencyLabel = (frequency: ReportSchedule): string => {
  switch (frequency) {
    case 'daily':
      return 'Daily';
    case 'weekly':
      return 'Weekly';
    case 'monthly':
      return 'Monthly';
    default:
      return frequency;
  }
};

const getFrequencyIcon = (frequency: ReportSchedule) => {
  switch (frequency) {
    case 'daily':
    case 'weekly':
    case 'monthly':
      return <Calendar className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getDayOfWeekLabel = (day?: number): string => {
  if (day === undefined) return '';
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return days[day];
};

const getScheduleDescription = (config: ReportScheduleConfig): string => {
  const parts: string[] = [];

  if (config.frequency === 'daily' && config.time) {
    parts.push(`at ${config.time}`);
  } else if (config.frequency === 'weekly') {
    if (config.dayOfWeek !== undefined) {
      parts.push(`on ${getDayOfWeekLabel(config.dayOfWeek)}`);
    }
    if (config.time) {
      parts.push(`at ${config.time}`);
    }
  } else if (config.frequency === 'monthly') {
    if (config.dayOfMonth) {
      const suffix =
        config.dayOfMonth === 1
          ? 'st'
          : config.dayOfMonth === 2
            ? 'nd'
            : config.dayOfMonth === 3
              ? 'rd'
              : 'th';
      parts.push(`on the ${config.dayOfMonth}${suffix}`);
    }
    if (config.time) {
      parts.push(`at ${config.time}`);
    }
  }

  return parts.join(' ');
};

const getReportTypeLabel = (type: ReportType): string => {
  switch (type) {
    case 'session':
      return 'Session';
    case 'trends':
      return 'Trends';
    case 'comparison':
      return 'Comparison';
    case 'error_analysis':
      return 'Error Analysis';
    default:
      return type;
  }
};

export function ScheduleCard({
  schedule,
  onEdit,
  onDelete,
  onToggle,
}: ScheduleCardProps) {
  const scheduleDescription = ''; // Backend handles schedule timing internally

  return (
    <Card className={`${schedule.enabled ? 'border-primary/50' : 'border-border'}`}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${
                schedule.enabled
                  ? 'bg-primary/20 text-primary'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {getFrequencyIcon(schedule.frequency)}
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                {schedule.name}
                {schedule.enabled ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-500" />
                )}
              </CardTitle>
              <p className="text-xs text-slate-400 mt-1">
                {schedule.enabled ? 'Active' : 'Disabled'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {onToggle && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onToggle(!schedule.enabled)}
                title={schedule.enabled ? 'Disable' : 'Enable'}
              >
                {schedule.enabled ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-500" />
                )}
              </Button>
            )}
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={onEdit} title="Edit schedule">
                <Edit className="h-4 w-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDelete}
                title="Delete schedule"
                className="text-red-500 hover:text-red-600 hover:bg-red-950/30"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Frequency & Schedule */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant={schedule.enabled ? 'default' : 'secondary'}>
              {getFrequencyLabel(schedule.frequency)}
            </Badge>
            {scheduleDescription && (
              <span className="text-sm text-slate-400">{scheduleDescription}</span>
            )}
          </div>
        </div>

        {/* Report Types */}
        <div>
          <p className="text-xs text-slate-400 mb-2">Report Types</p>
          <div className="flex flex-wrap gap-2">
            {schedule.reportTypes.map((type) => (
              <Badge key={type} variant="outline" className="capitalize">
                {getReportTypeLabel(type)}
              </Badge>
            ))}
          </div>
        </div>

        {/* Format */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-400">Format:</span>
            <Badge variant="secondary">{schedule.format.toUpperCase()}</Badge>
          </div>
        </div>

        {/* Retention */}
        <div className="pt-3 border-t border-slate-800">
          <p className="text-xs text-slate-500">
            Reports are retained for{' '}
            <span className="font-medium text-slate-400">{schedule.retentionDays} days</span>
          </p>
        </div>

        {/* Next Run (if enabled) */}
        {schedule.enabled && schedule.nextRunAt && (
          <div className="pt-3 border-t border-slate-800">
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Clock className="h-4 w-4" />
              <span>Next run: {new Date(schedule.nextRunAt).toLocaleString()}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
