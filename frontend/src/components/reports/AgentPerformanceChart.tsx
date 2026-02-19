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
import type { TrendData } from '@/types/reports';

interface AgentPerformanceChartProps {
  trends: TrendData;
  type?: 'bar' | 'pie';
}

const AGENT_COLORS: Record<string, string> = {
  ralph: '#3b82f6',
  claude: '#8b5cf6',
  cursor: '#06b6d4',
  terminal: '#f59e0b',
  crawler: '#10b981',
  analyzer: '#ec4899',
  reporter: '#6366f1',
  tester: '#f97316',
};

export function AgentPerformanceChart({ trends, type = 'bar' }: AgentPerformanceChartProps) {
  // Transform sessions by agent into chart data
  const chartData = Object.entries(trends.sessionsByAgent).map(([agent, count]) => ({
    agent: agent.charAt(0).toUpperCase() + agent.slice(1),
    sessions: count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-700 text-slate-500">
        No agent data available
      </div>
    );
  }

  if (type === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
            outerRadius={100}
            dataKey="sessions"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={AGENT_COLORS[entry.agent.toLowerCase()] || '#64748b'}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
            }}
            itemStyle={{ color: '#f1f5f9' }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number | undefined) => [value ?? 0, 'Sessions']}
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
          dataKey="agent"
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
          formatter={(value: number | undefined) => [value ?? 0, 'Sessions']}
        />
        <Legend
          wrapperStyle={{ color: '#94a3b8' }}
        />
        <Bar
          dataKey="sessions"
          fill="#3b82f6"
          radius={[4, 4, 0, 0]}
          name="Sessions"
        >
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={AGENT_COLORS[entry.agent.toLowerCase()] || '#64748b'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
