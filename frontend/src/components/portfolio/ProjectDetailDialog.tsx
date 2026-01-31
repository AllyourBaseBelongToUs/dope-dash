import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Clock,
  Activity,
  CheckCircle2,
  AlertCircle,
  Pause,
  X,
  RefreshCw,
  Trash2,
  Terminal,
} from 'lucide-react';
import type { ProjectDetail, ProjectStatus } from '@/types';
import { formatDistanceToNow } from 'date-fns';
import { ProjectControls } from './ProjectControls';
import { ProjectControlHistory } from './ProjectControlHistory';
import { CommandHistory } from '@/components/commands';
import { useState } from 'react';

interface ProjectDetailDialogProps {
  project: ProjectDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSync: () => void;
  onDelete: () => void;
  isUpdating?: boolean;
  onControlApplied?: () => void;
}

const getStatusColor = (status: ProjectStatus): string => {
  switch (status) {
    case 'idle':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    case 'running':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'paused':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'error':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'completed':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    default:
      return '';
  }
};

const getStatusIcon = (status: ProjectStatus) => {
  switch (status) {
    case 'idle':
      return <Clock className="h-4 w-4" />;
    case 'running':
      return <Activity className="h-4 w-4" />;
    case 'paused':
      return <Pause className="h-4 w-4" />;
    case 'error':
      return <AlertCircle className="h-4 w-4" />;
    case 'completed':
      return <CheckCircle2 className="h-4 w-4" />;
  }
};

export function ProjectDetailDialog({
  project,
  open,
  onOpenChange,
  onSync,
  onDelete,
  isUpdating,
  onControlApplied,
}: ProjectDetailDialogProps) {
  if (!project) return null;

  const [activeTab, setActiveTab] = useState<'overview' | 'commands'>('overview');
  const progressPercentage = Math.round(project.progress * 100);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <DialogTitle className="text-xl">{project.name}</DialogTitle>
              {project.description && (
                <DialogDescription className="mt-1">{project.description}</DialogDescription>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {/* Tabs */}
          <div className="flex gap-1 mt-4 border-b">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'overview'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('commands')}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'commands'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Terminal className="h-4 w-4" />
              Commands
            </button>
          </div>
        </DialogHeader>

        <div className="mt-4">
          {activeTab === 'overview' ? (
            <div className="space-y-6">
              {/* Status and Actions */}
              <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge className={getStatusColor(project.status)}>
                <span className="flex items-center gap-1.5">
                  {getStatusIcon(project.status)}
                  <span className="capitalize">{project.status}</span>
                </span>
              </Badge>
              <Badge variant="outline" className="capitalize">
                {project.priority}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onSync}
                disabled={isUpdating}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isUpdating ? 'animate-spin' : ''}`} />
                Sync
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onDelete}
                disabled={isUpdating}
                className="text-destructive hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Overall Progress</span>
              <span className="font-medium">{progressPercentage}%</span>
            </div>
            <div className="h-3 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            <div className="text-center text-sm text-muted-foreground">
              {project.completedSpecs} of {project.totalSpecs} specs completed
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="border border-border rounded-lg p-3">
              <div className="text-2xl font-bold">{project.activeAgents}</div>
              <div className="text-xs text-muted-foreground">Active Agents</div>
            </div>
            <div className="border border-border rounded-lg p-3">
              <div className="text-2xl font-bold">{project.stats.totalSessions}</div>
              <div className="text-xs text-muted-foreground">Total Sessions</div>
            </div>
            <div className="border border-border rounded-lg p-3">
              <div className="text-2xl font-bold">{project.stats.activeSessions}</div>
              <div className="text-xs text-muted-foreground">Active Sessions</div>
            </div>
            <div className="border border-border rounded-lg p-3">
              <div className="text-2xl font-bold">
                {project.lastActivityAt
                  ? formatDistanceToNow(new Date(project.lastActivityAt), { addSuffix: true })
                  : 'Never'}
              </div>
              <div className="text-xs text-muted-foreground">Last Activity</div>
            </div>
          </div>

          {/* Recent Sessions */}
          {project.recentSessions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-3">Recent Sessions</h3>
              <div className="border border-border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Started</TableHead>
                      <TableHead>Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {project.recentSessions.map((session) => (
                      <TableRow key={session.id}>
                        <TableCell className="font-medium capitalize">{session.agentType}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">
                            {session.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {session.startedAt
                            ? formatDistanceToNow(new Date(session.startedAt), { addSuffix: true })
                            : 'Unknown'}
                        </TableCell>
                        <TableCell>
                          {session.startedAt && session.endedAt
                            ? formatDistanceToNow(new Date(session.startedAt), {
                                addSuffix: false,
                              }).replace('ago', '') + ' total'
                            : session.startedAt
                            ? 'Running...'
                            : 'Unknown'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Project Controls */}
          <div>
            <h3 className="text-sm font-medium mb-3">Project Controls</h3>
            <ProjectControls project={project} onControlApplied={onControlApplied} />
          </div>

          {/* Control History */}
          <ProjectControlHistory projectId={project.id} />

          {/* Metadata */}
          {project.metadata && Object.keys(project.metadata).length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-3">Metadata</h3>
              <div className="border border-border rounded-lg p-3">
                <pre className="text-xs text-muted-foreground overflow-x-auto">
                  {JSON.stringify(project.metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="text-xs text-muted-foreground space-y-1">
            <div>Created: {new Date(project.createdAt).toLocaleString()}</div>
            <div>Updated: {new Date(project.updatedAt).toLocaleString()}</div>
          </div>
        </div>
          ) : (
            <CommandHistory projectId={project.id} onCommandReplayed={() => {}} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
