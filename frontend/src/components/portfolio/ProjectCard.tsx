'use client';

import { useDroppable } from '@dnd-kit/core';
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
  UserPlus,
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
import { cn } from '@/lib/utils';

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
  /** Whether the card accepts drag-and-drop agent assignments (default: true) */
  droppable?: boolean;
  /** Callback when an agent is dropped on this project */
  onAgentDrop?: (agentId: string, projectId: string) => void;
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

export function ProjectCard({
  project,
  onView,
  onSync,
  onDelete,
  isUpdating,
  onControlApplied,
  isSelected,
  onToggleSelection,
  isBulkMode,
  droppable = true,
  onAgentDrop,
}: ProjectCardProps) {
  const progressPercentage = Math.round(project.progress * 100);

  // Setup droppable for agent assignment
  const { setNodeRef, isOver, active } = useDroppable({
    id: `project-${project.id}`,
    data: {
      type: 'project',
      projectId: project.id,
      projectName: project.name,
      project,
    },
    disabled: !droppable,
  });

  // Check if this is a valid drop target (agent being dragged)
  const dragType = active?.data.current?.type;
  const isValidDrop = !droppable ? false : dragType === 'agent';
  const showDropIndicator = isOver && isValidDrop;

  return (
    <Card
      ref={setNodeRef}
      className={cn(
        'group hover:border-primary/50 transition-all',
        isSelected && 'ring-2 ring-primary',
        showDropIndicator && 'ring-2 ring-green-500 bg-green-500/5 border-green-500/50',
        isOver && !isValidDrop && 'ring-2 ring-red-500 bg-red-500/5 border-red-500/50'
      )}
    >
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
                <p className="text-sm truncate mt-1" style={{ color: 'var(--font-color)' }}>
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
            <span style={{ color: 'var(--font-color)' }}>Progress</span>
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
          <div className="text-right text-xs" style={{ color: 'var(--chart-overlay-color)' }}>
            {progressPercentage}% complete
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Activity className="h-4 w-4" style={{ color: 'var(--chart-overlay-color)' }} />
            <div>
              <div className="text-xs" style={{ color: 'var(--font-color)' }}>Active Agents</div>
              <div className="font-medium">{project.activeAgents}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4" style={{ color: 'var(--chart-overlay-color)' }} />
            <div>
              <div className="text-xs" style={{ color: 'var(--font-color)' }}>Last Activity</div>
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
