import type { Session } from '@/types';
import { ProgressBar } from './ProgressBar';
import { ControlButtons } from './ControlButtons';
import { useDashboardStore } from '@/store/dashboardStore';
import { Activity, Clock, AlertCircle, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface SessionCardProps {
  session: Session;
  isActive?: boolean;
}

export function SessionCard({ session, isActive = false }: SessionCardProps) {
  const { getSessionErrors } = useDashboardStore();
  const sessionErrors = getSessionErrors(session.id);
  const errorCount = sessionErrors.length;

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatDuration = (startedAt: string, endedAt?: string) => {
    const start = new Date(startedAt);
    const end = endedAt ? new Date(endedAt) : new Date();
    const diff = end.getTime() - start.getTime();

    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  };

  const getStatusIcon = () => {
    switch (session.status) {
      case 'running':
        return <Activity className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <XCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = () => {
    switch (session.status) {
      case 'running':
        return 'border-blue-500/50 bg-blue-950/20';
      case 'completed':
        return 'border-green-500/50 bg-green-950/20';
      case 'failed':
        return 'border-red-500/50 bg-red-950/20';
      case 'cancelled':
        return 'border-yellow-500/50 bg-yellow-950/20';
      default:
        return 'border-border bg-card';
    }
  };

  return (
    <div
      className={`rounded-lg border-2 p-4 transition-all ${
        isActive ? 'ring-2 ring-primary/50' : ''
      } ${getStatusColor()}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            {getStatusIcon()}
            {errorCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
                {errorCount > 9 ? '9+' : errorCount}
              </span>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              {session.projectName}
              {errorCount > 0 && (
                <span className="flex items-center gap-1 text-xs text-red-400 font-normal">
                  {errorCount === 1 ? (
                    <AlertCircle className="h-3 w-3" />
                  ) : (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  {errorCount}
                </span>
              )}
            </h3>
            <p className="text-xs text-muted-foreground font-mono">
              {session.id.slice(0, 8)}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground capitalize">
            {session.status}
          </div>
          <div className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDuration(session.startedAt, session.endedAt)}
          </div>
        </div>
      </div>

      <ProgressBar
        specs={session.specs}
        completedSpecs={session.completedSpecs}
        totalSpecs={session.totalSpecs}
        progress={session.progress}
        currentSpec={session.currentSpec}
      />

      {session.error && (
        <div className="mt-4 flex items-start gap-2 p-3 bg-red-950/30 border border-red-900/50 rounded-md">
          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-400">Error</p>
            <p className="text-xs text-red-300/80 mt-1">{session.error}</p>
          </div>
        </div>
      )}

      {/* Control Buttons - Only show for active sessions */}
      {session.status === 'running' && (
        <div className="mt-4">
          <ControlButtons session={session} />
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div>
          <span className="font-medium">Agent:</span> {session.agentType}
        </div>
        <div>
          <span className="font-medium">Started:</span> {formatTimestamp(session.startedAt)}
        </div>
      </div>
    </div>
  );
}
