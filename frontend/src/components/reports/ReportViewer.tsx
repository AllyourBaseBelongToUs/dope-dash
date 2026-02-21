'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Report, ReportFormat } from '@/types/reports';
import { Download, Maximize2, FileText, FileJson } from 'lucide-react';
import { SessionDurationChart, EventBreakdownChart, TrendChart, ComparisonChart } from './Charts';

interface ReportViewerProps {
  report: Report;
  onClose?: () => void;
  onDownload?: (reportId: string) => void;
}

const getFormatIcon = (format: ReportFormat) => {
  switch (format) {
    case 'pdf':
    case 'markdown':
      return <FileText className="h-5 w-5" />;
    case 'json':
      return <FileJson className="h-5 w-5" />;
    default:
      return <FileText className="h-5 w-5" />;
  }
};

const formatMarkdown = (content: string): string => {
  return content;
};

export function ReportViewer({ report, onClose, onDownload }: ReportViewerProps) {
  const [viewMode, setViewMode] = useState<'preview' | 'raw'>('preview');

  if (!report.data) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getFormatIcon(report.format)}
              {report.title}
            </div>
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <FileText className="h-12 w-12 mb-3 opacity-50" />
            <p className="text-lg font-medium">Report data not available</p>
            <p className="text-sm mt-1">This report may still be generating</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const renderContent = () => {
    if (report.format === 'json') {
      return (
        <pre className="bg-slate-950 p-4 rounded-lg overflow-x-auto text-sm text-slate-300">
          {JSON.stringify(report.data, null, 2)}
        </pre>
      );
    }

    // For markdown and pdf, render preview
    return (
      <div className="space-y-6">
        {/* Report Header */}
        <div className="border-b pb-4">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold">{report.data?.title ?? report.title}</h2>
              <p className="text-sm text-slate-400 mt-1">
                Generated: {new Date(report.data?.generatedAt ?? report.createdAt).toLocaleString()}
              </p>
            </div>
            <Badge variant="secondary" className="capitalize">
              {report.type.replace('_', ' ')}
            </Badge>
          </div>
        </div>

        {/* Charts Section */}
        {report.data?.charts && report.data?.charts.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Visualizations</h3>
            {report.data?.charts.map((chart, index) => (
              <Card key={index} className="bg-slate-950/50 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-base">{chart.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  {renderChart(chart)}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Sessions Summary */}
        {report.data?.sessions && report.data?.sessions.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Session Summary</h3>
            <div className="grid gap-4">
              {report.data?.sessions.map((session) => (
                <Card key={session.sessionId} className="bg-slate-950/50 border-slate-800">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-semibold">{session.projectName}</h4>
                        <p className="text-xs text-slate-400 font-mono mt-1">
                          {session.sessionId.slice(0, 8)}
                        </p>
                      </div>
                      <Badge
                        variant={session.status === 'completed' ? 'default' : 'secondary'}
                        className="capitalize"
                      >
                        {session.status}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400">Duration:</span>{' '}
                        <span className="font-medium">
                          {Math.round(session.duration / 60)}m {session.duration % 60}s
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Specs:</span>{' '}
                        <span className="font-medium">
                          {session.completedSpecs}/{session.totalSpecs}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Success Rate:</span>{' '}
                        <span className="font-medium">
                          {session.specSuccessRate.toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Errors:</span>{' '}
                        <span className="font-medium">{session.errorCount}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Trends Section */}
        {report.data?.trends && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Trends Overview</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Total Sessions</p>
                  <p className="text-2xl font-bold">{report.data?.trends.totalSessions}</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Avg Duration</p>
                  <p className="text-2xl font-bold">
                    {Math.round(report.data?.trends.avgSessionDuration / 60)}m
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Total Specs</p>
                  <p className="text-2xl font-bold">{report.data?.trends.totalSpecRuns}</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Success Rate</p>
                  <p className="text-2xl font-bold">
                    {report.data?.trends.specSuccessRate.toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Comparison Section */}
        {report.data?.comparison && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Comparison Metrics</h3>
            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Avg Duration</p>
                  <p className="text-xl font-bold">
                    {Math.round(report.data?.comparison.metrics.avgDuration / 60)}m
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-slate-950/50 border-slate-800">
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-400">Avg Success Rate</p>
                  <p className="text-xl font-bold">
                    {report.data?.comparison.metrics.avgSpecSuccessRate.toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Error Analysis Section */}
        {report.data?.errorAnalysis && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Error Analysis</h3>
            <Card className="bg-slate-950/50 border-slate-800">
              <CardContent className="pt-4">
                <p className="text-xs text-slate-400">Total Errors</p>
                <p className="text-2xl font-bold">{report.data?.errorAnalysis.totalErrors}</p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    );
  };

  const renderChart = (chart: any) => {
    // Simple chart rendering based on type
    // In a real implementation, you'd parse the chart data and render appropriate components
    return (
      <div className="text-sm text-slate-400">
        <p>Chart: {chart.title}</p>
        <p className="text-xs">Type: {chart.type}</p>
      </div>
    );
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getFormatIcon(report.format)}
            <div>
              <CardTitle>{report.title}</CardTitle>
              <p className="text-xs text-slate-400 mt-1">
                {new Date(report.createdAt).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onDownload && report.status === 'completed' && (
              <Button variant="outline" size="sm" onClick={() => onDownload(report.id)}>
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            )}
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="max-h-[70vh] overflow-y-auto">
        {renderContent()}
      </CardContent>
    </Card>
  );
}
