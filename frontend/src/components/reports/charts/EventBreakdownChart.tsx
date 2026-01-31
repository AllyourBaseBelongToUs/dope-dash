'use client';

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { Activity } from 'lucide-react';

interface EventBreakdownData {
  eventType: string;
  count: number;
  color?: string;
}

interface EventBreakdownChartProps {
  data: EventBreakdownData[];
  height?: number;
}

const DEFAULT_COLORS = [
  '#3b82f6', // blue-500
  '#22c55e', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#f97316', // orange-500
];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-white">{data.name}</p>
        <p className="text-sm text-slate-300 mt-1 flex items-center gap-1">
          <Activity className="h-3 w-3" />
          {data.value} events
        </p>
        <p className="text-xs text-slate-500 mt-1">
          {((data.payload.percent * 100).toFixed(1))}%
        </p>
      </div>
    );
  }
  return null;
};

const CustomLegend = ({ payload }: any) => {
  return (
    <div className="flex flex-wrap justify-center gap-4 mt-4">
      {payload.map((entry: any, index: number) => (
        <div key={index} className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-xs text-slate-400">{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

export function EventBreakdownChart({
  data,
  height = 300,
}: EventBreakdownChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-slate-500"
        style={{ height }}
      >
        <Activity className="h-12 w-12 mb-2 opacity-50" />
        <p className="text-sm">No event data available</p>
      </div>
    );
  }

  const chartData = data.map((item, index) => ({
    name: item.eventType,
    value: item.count,
    color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
  }));

  const totalEvents = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(props: any) => {
              const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;
              if (!cx || !cy || midAngle === undefined || !innerRadius || !outerRadius || percent === undefined) {
                return null;
              }

              const RADIAN = Math.PI / 180;
              const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
              const x = cx + radius * Math.cos(-midAngle * RADIAN);
              const y = cy + radius * Math.sin(-midAngle * RADIAN);

              if (percent < 0.05) return null; // Don't show label for small slices

              return (
                <text
                  x={x}
                  y={y}
                  fill="#fff"
                  textAnchor={x > cx ? 'start' : 'end'}
                  dominantBaseline="central"
                  fontSize={12}
                  fontWeight={500}
                >
                  {`${(percent * 100).toFixed(0)}%`}
                </text>
              );
            }}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="text-center mt-4">
        <p className="text-sm text-slate-400">
          Total Events: <span className="font-semibold text-white">{totalEvents}</span>
        </p>
      </div>
    </div>
  );
}
