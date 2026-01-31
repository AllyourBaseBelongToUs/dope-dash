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
  Cell,
} from 'recharts';
import { Clock } from 'lucide-react';

interface SessionDurationData {
  sessionId: string;
  projectName: string;
  duration: number;
  status: string;
}

interface SessionDurationChartProps {
  data: SessionDurationData[];
  height?: number;
}

const formatDuration = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'running':
      return '#3b82f6'; // blue-500
    case 'completed':
      return '#22c55e'; // green-500
    case 'failed':
      return '#ef4444'; // red-500
    case 'cancelled':
      return '#eab308'; // yellow-500
    default:
      return '#64748b'; // slate-500
  }
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-white">{data.projectName}</p>
        <p className="text-xs text-slate-400 mt-1">Session: {data.sessionId.slice(0, 8)}</p>
        <p className="text-sm text-slate-300 mt-2 flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDuration(data.duration)}
        </p>
        <p className="text-xs text-slate-500 mt-1 capitalize">{data.status}</p>
      </div>
    );
  }
  return null;
};

export function SessionDurationChart({
  data,
  height = 300,
}: SessionDurationChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-slate-500"
        style={{ height }}
      >
        <Clock className="h-12 w-12 mb-2 opacity-50" />
        <p className="text-sm">No session duration data available</p>
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: item.projectName.length > 15
      ? item.projectName.slice(0, 15) + '...'
      : item.projectName,
    duration: Math.round(item.duration),
    status: item.status,
    sessionId: item.sessionId,
    projectName: item.projectName,
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
            value: 'Duration (s)',
            angle: -90,
            position: 'insideLeft',
            fill: '#94a3b8',
            fontSize: 12,
          }}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155', fillOpacity: 0.2 }} />
        <Bar dataKey="duration" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getStatusColor(entry.status)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
