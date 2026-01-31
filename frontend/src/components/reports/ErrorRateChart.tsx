'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import type { TrendData } from '@/types/reports';
import { format } from 'date-fns';

interface ErrorRateChartProps {
  trends: TrendData;
  type?: 'line' | 'area';
}

export function ErrorRateChart({ trends, type = 'area' }: ErrorRateChartProps) {
  // Transform error trend data
  const chartData = trends.errorTrend.map((point) => ({
    date: format(new Date(point.timestamp), 'MMM dd HH:mm'),
    errors: point.count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-700 text-slate-500">
        No error trend data available
      </div>
    );
  }

  const Chart = type === 'area' ? AreaChart : LineChart;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <Chart data={chartData}>
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
          formatter={(value: number) => [value, 'Errors']}
        />
        <Legend
          wrapperStyle={{ color: '#94a3b8' }}
        />
        <Area
          type="monotone"
          dataKey="errors"
          stroke="#ef4444"
          fill="#ef4444"
          fillOpacity={0.3}
          name="Errors"
        />
      </Chart>
    </ResponsiveContainer>
  );
}
