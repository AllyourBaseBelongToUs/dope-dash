import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  MoreVertical,
  Clock,
  Activity,
  CheckCircle2,
  AlertCircle,
  Pause,
  Play,
  Eye,
  Trash2,
  RefreshCw,
  ListOrdered,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Project, ProjectStatus } from '@/types';
import { formatDistanceToNow } from 'date-fns';
import { ProjectControls } from './ProjectControls';

interface ProjectCardProps {
  project: Project;
  onView: (project: Project) => void;
  onSync: (projectId: string) => void;
  onDelete: (projectId: string) => void;
  isUpdating?: boolean;
  onControlApplied?: () => void;
  isSelected?: boolean;
  onToggleSelection?: (projectId: string) => void;
  isBulkMode?: boolean;
}

const getStatusColor = (status: ProjectStatus): string => {
  switch (status) {
    case 'idle':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    case 'queued':
      return 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20';
    case 'running':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'paused':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'error':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'completed':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    case 'cancelled':
      return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
    default:
      return '';
  }
};

const getPriorityColor = (priority: string): string => {
  switch (priority) {
    case 'low':
      return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
    case 'medium':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'high':
      return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'critical':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    default:
      return '';
  }
};

const getStatusIcon = (status: ProjectStatus) => {
  switch (status) {
    case 'idle':
      return <Clock className="h-3 w-3" />;
    case 'queued':
      return <ListOrdered className="h-3 w-3" />;
    case 'running':
      return <Activity className="h-3 w-3 animate-pulse" />;
    case 'paused':
      return <Pause className="h-3 w-3" />;
    case 'error':
      return <AlertCircle className="h-3 w-3" />;
    case 'completed':
      return <CheckCircle2 className="h-3 w-3" />;
    case 'cancelled':
      return <XCircle className="h-3 w-3" />;
  }
};

export function ProjectCard({ project, onView, onSync, onDelete, isUpdating, onControlApplied, isSelected, onToggleSelection, isBulkMode }: ProjectCardProps) {
  const progressPercentage = Math.round(project.progress * 100);

  return (
    <Card className={`group hover:border-primary/50 transition-colors ${isSelected ? 'ring-2 ring-primary' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {isBulkMode && onToggleSelection && (
              <Checkbox
                checked={isSelected}
                onChange={() => onToggleSelection(project.id)}
                className="shrink-0 mt-1"
                onClick={(e) => e.stopPropagation()}
              />
            )}
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate flex items-center gap-2">
                {project.name}
              </CardTitle>
              {project.description && (
                <p className="text-sm text-muted-foreground truncate mt-1">
                  {project.description}
                </p>
              )}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onView(project)}>
                <Eye className="h-4 w-4 mr-2" />
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onSync(project.id)}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Sync
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onDelete(project.id)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Status and Priority Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge className={getStatusColor(project.status)}>
            <span className="flex items-center gap-1">
              {getStatusIcon(project.status)}
              {project.status}
            </span>
          </Badge>
          <Badge className={getPriorityColor(project.priority)} variant="outline">
            {project.priority}
          </Badge>
          {/* Auto-paused indicator */}
          {project.metadata && Boolean(project.metadata.auto_paused) && (
            <Badge className="bg-orange-500/10 text-orange-500 border-orange-500/20" variant="outline">
              <span className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Auto-paused
              </span>
            </Badge>
          )}
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">
              {project.completedSpecs} / {project.totalSpecs} specs
            </span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <div className="text-right text-xs text-muted-foreground">
            {progressPercentage}% complete
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="text-muted-foreground text-xs">Active Agents</div>
              <div className="font-medium">{project.activeAgents}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="text-muted-foreground text-xs">Last Activity</div>
              <div className="font-medium">
                {project.lastActivityAt
                  ? formatDistanceToNow(new Date(project.lastActivityAt), { addSuffix: true })
                  : 'Never'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-0 flex flex-col gap-3">
        {/* Project Controls */}
        <ProjectControls project={project} onControlApplied={onControlApplied} />

        {/* View Project Button */}
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onView(project)}
        >
          View Project
        </Button>
      </CardFooter>
    </Card>
  );
}
