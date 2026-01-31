'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart,
} from 'recharts';
import { TrendingUp } from 'lucide-react';

interface TrendDataPoint {
  timestamp: string;
  count: number;
  completed?: number;
  failed?: number;
}

interface TrendChartProps {
  data: TrendDataPoint[];
  height?: number;
  showArea?: boolean;
  type?: 'sessions' | 'specs' | 'errors';
}

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const CustomTooltip = ({ active, payload, label, type }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-white">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm mt-1" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function TrendChart({
  data,
  height = 300,
  showArea = false,
  type = 'sessions',
}: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-slate-500"
        style={{ height }}
      >
        <TrendingUp className="h-12 w-12 mb-2 opacity-50" />
        <p className="text-sm">No trend data available</p>
      </div>
    );
  }

  const chartData = data.map((item) => ({
    ...item,
    formattedDate: formatTimestamp(item.timestamp),
  }));

  const hasBreakdown = chartData.some((item) => item.completed !== undefined);

  const ChartComponent = showArea ? AreaChart : LineChart;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ChartComponent data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.3} />
        <XAxis
          dataKey="formattedDate"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <YAxis
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <Tooltip content={<CustomTooltip type={type} />} cursor={{ fill: '#334155', fillOpacity: 0.2 }} />
        <Legend
          wrapperStyle={{ paddingTop: '20px' }}
          iconType="line"
        />
        {hasBreakdown ? (
          <>
            {showArea ? (
              <>
                <Area
                  type="monotone"
                  dataKey="completed"
                  stackId="1"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.3}
                  name="Completed"
                />
                <Area
                  type="monotone"
                  dataKey="failed"
                  stackId="1"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.3}
                  name="Failed"
                />
              </>
            ) : (
              <>
                <Line
                  type="monotone"
                  dataKey="completed"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ fill: '#22c55e', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Completed"
                />
                <Line
                  type="monotone"
                  dataKey="failed"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ fill: '#ef4444', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Failed"
                />
              </>
            )}
          </>
        ) : (
          <>
            {showArea ? (
              <Area
                type="monotone"
                dataKey="count"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.3}
                name={type === 'sessions' ? 'Sessions' : type === 'specs' ? 'Specs' : 'Errors'}
              />
            ) : (
              <Line
                type="monotone"
                dataKey="count"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 4 }}
                activeDot={{ r: 6 }}
                name={type === 'sessions' ? 'Sessions' : type === 'specs' ? 'Specs' : 'Errors'}
              />
            )}
          </>
        )}
      </ChartComponent>
    </ResponsiveContainer>
  );
}
