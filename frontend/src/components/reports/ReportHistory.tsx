'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { Report, ReportFormat } from '@/types/reports';
import {
  Download,
  FileText,
  Trash2,
  Calendar,
  FileJson,
  FileType,
} from 'lucide-react';
import { format } from 'date-fns';

/**
 * Report History Component
 * Displays list of generated reports with actions
 */

interface ReportHistoryProps {
  reports: Report[];
  selectedReport?: Report | null;
  onSelectReport?: (report: Report | null) => void;
  onDownload: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  isGenerating?: boolean;
}

export function ReportHistory({
  reports,
  selectedReport,
  onSelectReport,
  onDownload,
  onDelete,
  isGenerating = false,
}: ReportHistoryProps) {
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed'>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [downloading, setDownloading] = useState<string | null>(null);

  const filteredReports = reports
    .filter((r) => {
      if (filter === 'completed') return r.status === 'completed';
      if (filter === 'failed') return r.status === 'failed';
      return true;
    })
    .filter((r) => {
      if (typeFilter === 'all') return true;
      return r.type === typeFilter;
    });

  const handleDownload = async (reportId: string) => {
    setDownloading(reportId);
    try {
      await onDownload(reportId);
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = (reportId: string) => {
    if (confirm('Are you sure you want to delete this report?')) {
      onDelete(reportId);
    }
  };

  const getStatusBadge = (status: Report['status']) => {
    const variants = {
      pending: 'secondary',
      generating: 'default',
      completed: 'default',
      failed: 'destructive',
    } as const;

    const labels = {
      pending: 'Pending',
      generating: 'Generating',
      completed: 'Completed',
      failed: 'Failed',
    };

    return (
      <Badge variant={variants[status] as any}>
        {labels[status]}
      </Badge>
    );
  };

  const getTypeIcon = (format: ReportFormat) => {
    switch (format) {
      case 'pdf':
        return <FileText className="h-4 w-4 text-red-500" />;
      case 'markdown':
        return <FileType className="h-4 w-4 text-blue-500" />;
      case 'json':
        return <FileJson className="h-4 w-4 text-yellow-500" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Report History</CardTitle>
            <CardDescription>
              View and download previously generated reports
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Select value={filter} onValueChange={(v) => setFilter(v as any)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="session">Session</SelectItem>
                <SelectItem value="trends">Trends</SelectItem>
                <SelectItem value="comparison">Comparison</SelectItem>
                <SelectItem value="error_analysis">Error Analysis</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filteredReports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No reports found</p>
            <p className="text-sm text-muted-foreground">
              Generate your first report to see it here
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReports.map((report) => (
                <TableRow
                  key={report.id}
                  className={selectedReport?.id === report.id ? 'bg-muted' : ''}
                  onClick={() => onSelectReport?.(report)}
                  style={{ cursor: onSelectReport ? 'pointer' : 'default' }}
                >
                  <TableCell className="font-medium">{report.title}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{report.type}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      {getTypeIcon(report.format)}
                      <span className="text-xs uppercase">{report.format}</span>
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(report.status)}</TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      <span>{format(new Date(report.createdAt), 'MMM dd, HH:mm')}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end space-x-1">
                      {report.status === 'completed' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(report.id)}
                          disabled={downloading === report.id || isGenerating}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(report.id)}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
