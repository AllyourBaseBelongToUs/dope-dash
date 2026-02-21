import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Pause,
  Play,
  SkipForward,
  Square,
  RotateCcw,
  RotateCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  ListOrdered,
} from 'lucide-react';
import { usePortfolioStore } from '@/store/portfolioStore';
import type { ProjectControlHistoryEntry, ProjectControlAction } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface ProjectControlHistoryProps {
  projectId: string;
}

const controlIcons: Record<ProjectControlAction, React.ComponentType<{ className?: string }>> = {
  pause: Pause,
  resume: Play,
  skip: SkipForward,
  stop: Square,
  retry: RotateCcw,
  restart: RotateCw,
  queue: ListOrdered,
  cancel: XCircle,
};

const controlLabels: Record<ProjectControlAction, string> = {
  pause: 'Paused',
  resume: 'Resumed',
  skip: 'Skipped',
  stop: 'Stopped',
  retry: 'Retried',
  restart: 'Restarted',
  queue: 'Queued',
  cancel: 'Cancelled',
};

const statusConfig = {
  pending: {
    icon: Loader2,
    label: 'Pending',
    className: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    iconClassName: 'animate-spin',
  },
  acknowledged: {
    icon: Clock,
    label: 'Acknowledged',
    className: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    iconClassName: '',
  },
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    className: 'bg-green-500/10 text-green-500 border-green-500/20',
    iconClassName: '',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    className: 'bg-red-500/10 text-red-500 border-red-500/20',
    iconClassName: '',
  },
  timeout: {
    icon: AlertTriangle,
    label: 'Timeout',
    className: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    iconClassName: '',
  },
};

export function ProjectControlHistory({ projectId }: ProjectControlHistoryProps) {
  const [controls, setControls] = useState<ProjectControlHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const fetchProjectControls = usePortfolioStore((state) => state.fetchProjectControls);

  useEffect(() => {
    const loadControls = async () => {
      setIsLoading(true);
      try {
        const data = await fetchProjectControls(projectId, 20);
        setControls(data);
      } finally {
        setIsLoading(false);
      }
    };

    loadControls();
  }, [projectId, fetchProjectControls]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Control History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (controls.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Control History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No control actions recorded yet
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Control History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] overflow-y-auto pr-2">
          <div className="space-y-3">
            {controls.map((entry) => {
              const ControlIcon = controlIcons[entry.action];
              const statusConf = statusConfig[entry.status];
              const StatusIcon = statusConf.icon;

              return (
                <div
                  key={entry.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="p-2 rounded-md bg-background border">
                      <ControlIcon className="h-4 w-4" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium capitalize">
                        {controlLabels[entry.action]}
                      </span>
                      <Badge className={statusConf.className} variant="outline">
                        <StatusIcon className={`h-3 w-3 mr-1 ${statusConf.iconClassName}`} />
                        {statusConf.label}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(new Date(entry.createdAt), { addSuffix: true })}
                      </span>
                      {entry.agentsAffected > 0 && (
                        <span>
                          {entry.agentsAffected} agent{entry.agentsAffected > 1 ? 's' : ''} affected
                        </span>
                      )}
                      <span>by {entry.initiatedBy}</span>
                    </div>

                    {entry.errorMessage && (
                      <div className="mt-2 text-sm text-destructive flex items-start gap-1">
                        <XCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span>{entry.errorMessage}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
