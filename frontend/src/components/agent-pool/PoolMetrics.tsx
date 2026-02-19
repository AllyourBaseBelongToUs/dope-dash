'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import type { PoolMetrics, PoolHealthReport } from '@/types';
import {
  Server,
  Activity,
  CheckCircle2,
  XCircle,
  Wrench,
  ArrowDownToLine,
  Gauge,
  TrendingUp,
  AlertTriangle,
  HeartPulse,
} from 'lucide-react';

interface PoolMetricsProps {
  metrics: PoolMetrics | null;
  healthReport: PoolHealthReport | null;
}

export function PoolMetrics({ metrics, healthReport }: PoolMetricsProps) {
  const getUtilizationColor = (percent: number) => {
    if (percent >= 80) return 'text-red-500';
    if (percent >= 60) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getUtilizationVariant = (percent: number): 'default' | 'secondary' | 'destructive' => {
    if (percent >= 80) return 'destructive';
    if (percent >= 60) return 'default';
    return 'secondary';
  };

  const getHealthBadge = () => {
    if (!healthReport) return null;
    const { healthy } = healthReport;

    return (
      <Badge variant={healthy ? 'default' : 'destructive'} className="gap-1.5">
        {healthy ? (
          <>
            <HeartPulse className="h-3 w-3" />
            Healthy
          </>
        ) : (
          <>
            <AlertTriangle className="h-3 w-3" />
            Issues Detected
          </>
        )}
      </Badge>
    );
  };

  if (!metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <div className="h-4 w-24 bg-muted animate-pulse rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted animate-pulse rounded mb-2" />
              <div className="h-2 w-full bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Health Status */}
      {healthReport && (
        <Card className={healthReport.healthy ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <HeartPulse className="h-4 w-4" />
                Pool Health
              </CardTitle>
              {getHealthBadge()}
            </div>
          </CardHeader>
          {(!healthReport.healthy || healthReport.recommendations.length > 0) && (
            <CardContent className="space-y-2">
              {healthReport.issues.map((issue, i) => (
                <div key={i} className="text-xs text-red-600 dark:text-red-400 flex items-start gap-2">
                  <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                  <span>{issue}</span>
                </div>
              ))}
              {healthReport.recommendations.map((rec, i) => (
                <div key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                  <TrendingUp className="h-3 w-3 mt-0.5 flex-shrink-0" />
                  <span>{rec}</span>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Agents */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              Total Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">{metrics.totalAgents}</div>
              <Badge variant="secondary" className="text-xs">
                {metrics.availableAgents} available
              </Badge>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                  Available
                </span>
                <span className="font-medium">{metrics.availableAgents}</span>
              </div>
              <div className="flex justify-between">
                <span className="flex items-center gap-1">
                  <Activity className="h-3 w-3 text-blue-500" />
                  Busy
                </span>
                <span className="font-medium">{metrics.busyAgents}</span>
              </div>
              <div className="flex justify-between">
                <span className="flex items-center gap-1">
                  <XCircle className="h-3 w-3 text-red-500" />
                  Offline
                </span>
                <span className="font-medium">{metrics.offlineAgents}</span>
              </div>
              <div className="flex justify-between">
                <span className="flex items-center gap-1">
                  <Wrench className="h-3 w-3 text-yellow-500" />
                  Maintenance
                </span>
                <span className="font-medium">{metrics.maintenanceAgents}</span>
              </div>
              <div className="flex justify-between">
                <span className="flex items-center gap-1">
                  <ArrowDownToLine className="h-3 w-3 text-orange-500" />
                  Draining
                </span>
                <span className="font-medium">{metrics.drainingAgents}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Capacity */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Gauge className="h-4 w-4 text-muted-foreground" />
              Capacity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">{metrics.usedCapacity}</div>
              <div className="text-xs text-muted-foreground mb-1">
                of {metrics.totalCapacity} total
              </div>
            </div>
            <Progress
              value={metrics.utilizationPercent}
              className="mt-3 h-2"
            />
            <div className={`mt-2 text-sm font-medium ${getUtilizationColor(metrics.utilizationPercent)}`}>
              {metrics.utilizationPercent.toFixed(1)}% utilization
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {metrics.availableCapacity} slots available
            </div>
          </CardContent>
        </Card>

        {/* Completion Rate */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
              Success Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">
                {(metrics.averageCompletionRate * 100).toFixed(1)}%
              </div>
              <Badge variant={getUtilizationVariant(metrics.averageCompletionRate * 100)} className="text-xs">
                {metrics.averageCompletionRate >= 0.8 ? 'Excellent' : metrics.averageCompletionRate >= 0.6 ? 'Good' : 'Needs Attention'}
              </Badge>
            </div>
            <Progress
              value={metrics.averageCompletionRate * 100}
              className="mt-3 h-2"
            />
            <div className="mt-3 text-xs text-muted-foreground">
              Average task completion rate across all agents
            </div>
          </CardContent>
        </Card>

        {/* Agents by Type */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              By Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(metrics.agentsByType).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-muted-foreground">{type}</span>
                  <Badge variant="outline" className="text-xs">
                    {count}
                  </Badge>
                </div>
              ))}
              {Object.keys(metrics.agentsByType).length === 0 && (
                <div className="text-xs text-muted-foreground text-center py-2">
                  No agents registered
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
