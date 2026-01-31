'use client';

import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { TrendData, ComparisonData, ErrorAnalysisData } from '@/types/reports';
import { format } from 'date-fns';

/**
 * Chart colors
 */
const CHART_COLORS = {
  primary: '#3b82f6',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#8b5cf6',
  slate: '#64748b',
};

/**
 * Format date for chart display
 */
function formatChartDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'MMM dd');
  } catch {
    return dateString;
  }
}

/**
 * Session Trend Line Chart
 */
export function SessionTrendChart({ trends }: { trends: TrendData }) {
  const data = trends.sessionTrend.map((point) => ({
    date: formatChartDate(point.timestamp),
    sessions: point.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="sessions"
          stroke={CHART_COLORS.primary}
          strokeWidth={2}
          dot={{ fill: CHART_COLORS.primary }}
          name="Sessions"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/**
 * Spec Trend Area Chart
 */
export function SpecTrendChart({ trends }: { trends: TrendData }) {
  const data = trends.specTrend.map((point) => ({
    date: formatChartDate(point.timestamp),
    total: point.total,
    completed: point.completed,
    failed: point.failed,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="total"
          stackId="1"
          stroke={CHART_COLORS.slate}
          fill={CHART_COLORS.slate}
          fillOpacity={0.3}
          name="Total Specs"
        />
        <Area
          type="monotone"
          dataKey="completed"
          stackId="1"
          stroke={CHART_COLORS.success}
          fill={CHART_COLORS.success}
          fillOpacity={0.6}
          name="Completed"
        />
        <Area
          type="monotone"
          dataKey="failed"
          stackId="1"
          stroke={CHART_COLORS.danger}
          fill={CHART_COLORS.danger}
          fillOpacity={0.6}
          name="Failed"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Error Trend Bar Chart
 */
export function ErrorTrendChart({ trends }: { trends: TrendData }) {
  const data = trends.errorTrend.map((point) => ({
    date: formatChartDate(point.timestamp),
    errors: point.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Bar
          dataKey="errors"
          fill={CHART_COLORS.danger}
          name="Errors"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Sessions by Status Pie Chart
 */
export function SessionsByStatusChart({ trends }: { trends: TrendData }) {
  const data = Object.entries(trends.sessionsByStatus).map(([status, count]) => ({
    name: status,
    value: count,
  }));

  const COLORS = {
    completed: CHART_COLORS.success,
    running: CHART_COLORS.primary,
    failed: CHART_COLORS.danger,
    cancelled: CHART_COLORS.slate,
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry) => (
            <Cell
              key={`cell-${entry.name}`}
              fill={COLORS[entry.name as keyof typeof COLORS] || CHART_COLORS.info}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

/**
 * Sessions by Agent Bar Chart
 */
export function SessionsByAgentChart({ trends }: { trends: TrendData }) {
  const data = Object.entries(trends.sessionsByAgent).map(([agent, count]) => ({
    agent,
    count,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="agent"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Bar
          dataKey="count"
          fill={CHART_COLORS.primary}
          name="Sessions"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Comparison Metrics Bar Chart
 */
export function ComparisonMetricsChart({ comparison }: { comparison: ComparisonData }) {
  const data = comparison.sessions.map((session) => ({
    name: session.projectName.slice(0, 15),
    duration: Math.round(session.duration / 60),
    successRate: Math.round(session.specSuccessRate * 100),
    specs: session.completedSpecs,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="name"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          yAxisId="left"
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          yAxisId="right"
          orientation="right"
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Bar
          yAxisId="left"
          dataKey="duration"
          fill={CHART_COLORS.primary}
          name="Duration (min)"
          radius={[4, 4, 0, 0]}
        />
        <Bar
          yAxisId="right"
          dataKey="successRate"
          fill={CHART_COLORS.success}
          name="Success Rate (%)"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Top Errors Bar Chart
 */
export function TopErrorsChart({ errorAnalysis }: { errorAnalysis: ErrorAnalysisData }) {
  const data = errorAnalysis.topErrors.slice(0, 10).map((error, i) => ({
    index: i + 1,
    message: error.message.slice(0, 30) + (error.message.length > 30 ? '...' : ''),
    count: error.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          type="number"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey="message"
          stroke="#64748b"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Bar
          dataKey="count"
          fill={CHART_COLORS.danger}
          name="Error Count"
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Errors by Session Bar Chart
 */
export function ErrorsBySessionChart({ errorAnalysis }: { errorAnalysis: ErrorAnalysisData }) {
  const data = errorAnalysis.errorsBySession.slice(0, 15).map((session) => ({
    session: session.sessionId.slice(0, 10),
    count: session.errorCount,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="session"
          stroke="#64748b"
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
          }}
        />
        <Legend />
        <Bar
          dataKey="count"
          fill={CHART_COLORS.warning}
          name="Errors"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
