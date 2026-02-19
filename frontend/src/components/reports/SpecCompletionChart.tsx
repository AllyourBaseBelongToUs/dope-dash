'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import type { TrendData, SessionSummary } from '@/types/reports';

interface SpecCompletionChartProps {
  data?: TrendData | SessionSummary[];
  type?: 'bar' | 'pie';
}

const COLORS = {
  completed: '#22c55e',
  failed: '#ef4444',
  pending: '#94a3b8',
  running: '#3b82f6',
};

export function SpecCompletionChart({ data, type = 'bar' }: SpecCompletionChartProps) {
  if (!data) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-700 text-slate-500">
        No spec data available
      </div>
    );
  }

  // Handle TrendData
  if ('specTrend' in data) {
    const chartData = data.specTrend.slice(-15).map((point) => ({
      date: new Date(point.timestamp).toLocaleDateString(),
      completed: point.completed,
      failed: point.failed,
      total: point.total,
    }));

    if (type === 'pie') {
      const totalCompleted = chartData.reduce((sum, d) => sum + d.completed, 0);
      const totalFailed = chartData.reduce((sum, d) => sum + d.failed, 0);
      const pieData = [
        { name: 'Completed', value: totalCompleted },
        { name: 'Failed', value: totalFailed },
      ];

      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
              outerRadius={100}
              dataKey="value"
            >
              <Cell fill={COLORS.completed} />
              <Cell fill={COLORS.failed} />
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '6px',
              }}
              itemStyle={{ color: '#f1f5f9' }}
            />
          </PieChart>
        </ResponsiveContainer>
      );
    }

    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
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
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
            }}
            itemStyle={{ color: '#f1f5f9' }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Legend
            wrapperStyle={{ color: '#94a3b8' }}
          />
          <Bar dataKey="completed" fill={COLORS.completed} radius={[4, 4, 0, 0]} name="Completed" />
          <Bar dataKey="failed" fill={COLORS.failed} radius={[4, 4, 0, 0]} name="Failed" />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // Handle SessionSummary array
  const sessions = data as SessionSummary[];
  const chartData = sessions.slice(0, 15).map((session) => ({
    name: session.projectName.slice(0, 12),
    completed: session.completedSpecs,
    failed: session.failedSpecs,
    successRate: Math.round(session.specSuccessRate * 100),
  }));

  if (type === 'pie') {
    const totalCompleted = sessions.reduce((sum, s) => sum + s.completedSpecs, 0);
    const totalFailed = sessions.reduce((sum, s) => sum + s.failedSpecs, 0);
    const pieData = [
      { name: 'Completed', value: totalCompleted },
      { name: 'Failed', value: totalFailed },
    ];

    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
            outerRadius={100}
            dataKey="value"
          >
            <Cell fill={COLORS.completed} />
            <Cell fill={COLORS.failed} />
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
            }}
            itemStyle={{ color: '#f1f5f9' }}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          type="number"
          stroke="#94a3b8"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          stroke="#94a3b8"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '6px',
          }}
          itemStyle={{ color: '#f1f5f9' }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Legend
          wrapperStyle={{ color: '#94a3b8' }}
        />
        <Bar dataKey="completed" fill={COLORS.completed} radius={[0, 4, 4, 0]} name="Completed" />
        <Bar dataKey="failed" fill={COLORS.failed} radius={[0, 4, 4, 0]} name="Failed" />
      </BarChart>
    </ResponsiveContainer>
  );
}
