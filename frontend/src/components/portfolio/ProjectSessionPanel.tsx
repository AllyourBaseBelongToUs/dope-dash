'use client';

import { useDroppable } from '@dnd-kit/core';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Folder,
  MapPin,
  Link2,
  Coins,
  Clock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

export interface ProjectSessionData {
  id: string;
  name: string;
  path: string;
  completion: number; // 0-100
  linkedAgentId?: string;
  linkedAgentName?: string;
  linkedAgentColor?: string;
  tokensUsed?: number;
  lastActivity?: string;
  status: 'active' | 'idle' | 'completed' | 'error';
}

interface ProjectSessionPanelProps {
  project: ProjectSessionData;
  isHovered?: boolean;
  onClick?: () => void;
  /** Whether the panel accepts drag-and-drop agent assignments (default: true) */
  droppable?: boolean;
}

const getStatusColor = (status: ProjectSessionData['status']): string => {
  switch (status) {
    case 'active':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'idle':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    case 'completed':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    case 'error':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    default:
      return '';
  }
};

export function ProjectSessionPanel({ project, isHovered, onClick, droppable = true }: ProjectSessionPanelProps) {
  // Setup droppable for agent assignment
  const { setNodeRef, isOver } = useDroppable({
    id: `project-${project.id}`,
    data: {
      type: 'project',
      projectId: project.id,
      projectName: project.name,
      project,
    },
    disabled: !droppable,
  });

  // Shorten path for display
  const shortPath = project.path.length > 40
    ? `...${project.path.slice(-37)}`
    : project.path;

  return (
    <Card
      ref={setNodeRef}
      className={cn(
        'transition-all cursor-pointer',
        isHovered && 'ring-2 ring-primary/50',
        project.linkedAgentColor && `border-l-4`,
        isOver && 'ring-2 ring-green-500 bg-green-500/5',
        onClick && 'hover:shadow-md'
      )}
      style={
        project.linkedAgentColor
          ? { borderLeftColor: project.linkedAgentColor }
          : undefined
      }
      onClick={(e) => {
        // Prevent click if dragging just finished
        if (!isOver && onClick) {
          onClick();
        }
      }}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Folder className="h-4 w-4 text-muted-foreground" />
            {project.name}
          </CardTitle>
          <Badge className={getStatusColor(project.status)} variant="outline">
            {project.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {/* Path with tooltip */}
        <div
          className="flex items-center gap-2"
          style={{ color: 'var(--font-color)' }}
          title={project.path}
        >
          <MapPin className="h-3 w-3 flex-shrink-0" />
          <span className="truncate font-mono text-xs">{shortPath}</span>
        </div>

        {/* Completion Progress */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span style={{ color: 'var(--font-color)' }}>Completion</span>
            <span className="font-medium">{project.completion}%</span>
          </div>
          <Progress value={project.completion} className="h-1.5" />
        </div>

        {/* Linked Agent */}
        {project.linkedAgentName && (
          <div className="flex items-center gap-2">
            <Link2 className="h-3 w-3" style={{ color: 'var(--chart-overlay-color)' }} />
            <Badge
              variant="outline"
              className="text-xs"
              style={{ borderColor: project.linkedAgentColor }}
            >
              {project.linkedAgentName}
            </Badge>
          </div>
        )}

        {/* Tokens Used */}
        {project.tokensUsed !== undefined && (
          <div className="flex items-center gap-2">
            <Coins className="h-3 w-3" style={{ color: 'var(--chart-overlay-color)' }} />
            <span className="text-xs" style={{ color: 'var(--font-color)' }}>
              {project.tokensUsed.toLocaleString()} tokens
            </span>
          </div>
        )}

        {/* Last Activity */}
        {project.lastActivity && (
          <div className="flex items-center gap-2">
            <Clock className="h-3 w-3" style={{ color: 'var(--chart-overlay-color)' }} />
            <span className="text-xs" style={{ color: 'var(--font-color)' }}>
              {formatDistanceToNow(new Date(project.lastActivity), { addSuffix: true })}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
