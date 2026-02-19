'use client';

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { SessionSummary } from '@/types/reports';
import { format } from 'date-fns';

interface SessionDurationChartProps {
  sessions: SessionSummary[];
  type?: 'line' | 'bar';
}

export function SessionDurationChart({ sessions, type = 'bar' }: SessionDurationChartProps) {
  // Transform data for chart
  const chartData = sessions
    .map((session) => ({
      name: session.projectName.slice(0, 15),
      duration: Math.round(session.duration / 60), // Convert to minutes
      agent: session.agentType,
      date: format(new Date(session.startedAt), 'MMM dd'),
    }))
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 20); // Top 20

  const formatDuration = (value: number) => `${value}m`;

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-700 text-slate-500">
        No session data available
      </div>
    );
  }

  const Chart = type === 'line' ? LineChart : BarChart;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <Chart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="name"
          stroke="#94a3b8"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#94a3b8"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={formatDuration}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '6px',
          }}
          itemStyle={{ color: '#f1f5f9' }}
          labelStyle={{ color: '#94a3b8' }}
          formatter={(value: number | undefined) => [`${value ?? 0}m`, 'Duration']}
        />
        <Legend
          wrapperStyle={{ color: '#94a3b8' }}
        />
        <Bar
          dataKey="duration"
          fill="#3b82f6"
          radius={[4, 4, 0, 0]}
          name="Duration (min)"
        />
      </Chart>
    </ResponsiveContainer>
  );
}
