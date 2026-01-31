'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { BarChart3 } from 'lucide-react';

interface ComparisonDataPoint {
  sessionId: string;
  projectName: string;
  duration: number;
  specSuccessRate: number;
  totalSpecs: number;
  completedSpecs: number;
  failedSpecs: number;
  errorCount: number;
}

interface ComparisonChartProps {
  data: ComparisonDataPoint[];
  metric: 'duration' | 'specSuccessRate' | 'totalSpecs' | 'errorCount';
  height?: number;
}

const getMetricConfig = (metric: string) => {
  switch (metric) {
    case 'duration':
      return {
        label: 'Duration (s)',
        color: '#3b82f6',
        formatValue: (v: number) => `${v}s`,
      };
    case 'specSuccessRate':
      return {
        label: 'Success Rate (%)',
        color: '#22c55e',
        formatValue: (v: number) => `${v.toFixed(1)}%`,
      };
    case 'totalSpecs':
      return {
        label: 'Total Specs',
        color: '#8b5cf6',
        formatValue: (v: number) => v.toString(),
      };
    case 'errorCount':
      return {
        label: 'Errors',
        color: '#ef4444',
        formatValue: (v: number) => v.toString(),
      };
    default:
      return {
        label: metric,
        color: '#64748b',
        formatValue: (v: number) => v.toString(),
      };
  }
};

const CustomTooltip = ({ active, payload, metric }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const config = getMetricConfig(metric);
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-white">{data.projectName}</p>
        <p className="text-xs text-slate-400 mt-1">Session: {data.sessionId.slice(0, 8)}</p>
        <p className="text-sm text-slate-300 mt-2">{config.label}</p>
        <p className="text-lg font-semibold" style={{ color: config.color }}>
          {config.formatValue(data[metric])}
        </p>
        {metric !== 'specSuccessRate' && metric !== 'errorCount' && (
          <>
            <p className="text-xs text-slate-500 mt-2">Specs: {data.completedSpecs}/{data.totalSpecs}</p>
            <p className="text-xs text-slate-500">Success Rate: {data.specSuccessRate.toFixed(1)}%</p>
          </>
        )}
      </div>
    );
  }
  return null;
};

export function ComparisonChart({
  data,
  metric = 'duration',
  height = 300,
}: ComparisonChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-slate-500"
        style={{ height }}
      >
        <BarChart3 className="h-12 w-12 mb-2 opacity-50" />
        <p className="text-sm">No comparison data available</p>
      </div>
    );
  }

  const config = getMetricConfig(metric);

  const chartData = data.map((item) => ({
    name: item.projectName.length > 12
      ? item.projectName.slice(0, 12) + '...'
      : item.projectName,
    value: item[metric as keyof ComparisonDataPoint] as number,
    projectName: item.projectName,
    sessionId: item.sessionId,
    duration: item.duration,
    specSuccessRate: item.specSuccessRate,
    totalSpecs: item.totalSpecs,
    completedSpecs: item.completedSpecs,
    failedSpecs: item.failedSpecs,
    errorCount: item.errorCount,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.3} />
        <XAxis
          dataKey="name"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          angle={-45}
          textAnchor="end"
          height={60}
        />
        <YAxis
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{
            value: config.label,
            angle: -90,
            position: 'insideLeft',
            fill: '#94a3b8',
            fontSize: 12,
          }}
        />
        <Tooltip content={<CustomTooltip metric={metric} />} cursor={{ fill: '#334155', fillOpacity: 0.2 }} />
        <Legend
          wrapperStyle={{ paddingTop: '10px' }}
          iconType="circle"
        />
        <Bar
          dataKey="value"
          fill={config.color}
          radius={[4, 4, 0, 0]}
          name={config.label}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
