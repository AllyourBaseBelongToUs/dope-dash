import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  FolderOpen,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  Users,
  ListOrdered,
  XCircle,
} from 'lucide-react';
import type { ProjectSummary, ProjectStatus, ProjectPriority } from '@/types';

interface PortfolioSummaryProps {
  summary: ProjectSummary | null;
  isLoading?: boolean;
}

const statusIcons: Record<ProjectStatus, React.ReactNode> = {
  idle: <Clock className="h-4 w-4" />,
  queued: <ListOrdered className="h-4 w-4" />,
  running: <Activity className="h-4 w-4 animate-pulse" />,
  paused: <Clock className="h-4 w-4" />,
  error: <AlertTriangle className="h-4 w-4" />,
  completed: <CheckCircle2 className="h-4 w-4" />,
  cancelled: <XCircle className="h-4 w-4" />,
};

const statusColors: Record<ProjectStatus, string> = {
  idle: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
  queued: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
  running: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  paused: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  error: 'bg-red-500/10 text-red-500 border-red-500/20',
  completed: 'bg-green-500/10 text-green-500 border-green-500/20',
  cancelled: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
};

const priorityColors: Record<ProjectPriority, string> = {
  low: 'bg-slate-500/10 text-slate-500',
  medium: 'bg-blue-500/10 text-blue-500',
  high: 'bg-orange-500/10 text-orange-500',
  critical: 'bg-red-500/10 text-red-500',
};

export function PortfolioSummary({ summary, isLoading }: PortfolioSummaryProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted rounded w-24" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Total Projects
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.totalProjects}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Active Now
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-500">
              {summary.projectsByStatus?.running || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {summary.totalActiveAgents} agent{summary.totalActiveAgents !== 1 ? 's' : ''} running
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-500">
              {summary.projectsByStatus?.completed || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {Math.round(summary.avgProgress * 100)}% avg progress
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Spec Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {Math.round(summary.overallCompletionRate * 100)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {summary.completedSpecs} / {summary.totalSpecs} specs
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Status and Priority Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* By Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Projects by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(Object.entries(summary.projectsByStatus || {}) as [ProjectStatus, number][]).map(
                ([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <Badge className={statusColors[status]} variant="outline">
                      <span className="flex items-center gap-1.5">
                        {statusIcons[status]}
                        <span className="capitalize">{status}</span>
                      </span>
                    </Badge>
                    <span className="font-medium">{count}</span>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>

        {/* By Priority */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Projects by Priority</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(Object.entries(summary.projectsByPriority || {}) as [ProjectPriority, number][]).map(
                ([priority, count]) => (
                  <div key={priority} className="flex items-center justify-between">
                    <Badge className={priorityColors[priority]} variant="secondary">
                      <span className="capitalize">{priority}</span>
                    </Badge>
                    <span className="font-medium">{count}</span>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      {summary.recentActiveProjects > 0 && (
        <Card className="bg-blue-500/5 border-blue-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="bg-blue-500/10 p-2 rounded-full">
                <Activity className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="font-medium">{summary.recentActiveProjects} projects</p>
                <p className="text-sm text-muted-foreground">
                  had activity in the last 24 hours
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
