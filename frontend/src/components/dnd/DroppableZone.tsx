'use client';

import { useDroppable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface DroppableZoneProps {
  /** Unique identifier for this drop zone */
  id: string;
  /** Type of this drop zone (for validation) */
  type: 'agent' | 'project';
  /** Additional data to pass with the drop */
  data?: Record<string, unknown>;
  /** Content to render inside the drop zone */
  children: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Whether the drop zone is disabled */
  disabled?: boolean;
  /** Custom render when hovering/dragging over */
  renderOverlay?: (isOver: boolean) => ReactNode;
}

export function DroppableZone({
  id,
  type,
  data,
  children,
  className,
  disabled = false,
  renderOverlay,
}: DroppableZoneProps) {
  const { setNodeRef, isOver, active } = useDroppable({
    id,
    data: {
      type,
      ...data,
    },
    disabled,
  });

  // Check if this is a valid drop target
  const dragType = active?.data.current?.type;
  const isValidTarget =
    !disabled &&
    ((dragType === 'agent' && type === 'project') ||
      (dragType === 'project' && type === 'agent'));

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'relative transition-all',
        isOver && isValidTarget && 'ring-2 ring-primary bg-primary/5',
        isOver && !isValidTarget && 'ring-2 ring-red-500 bg-red-500/5',
        className
      )}
    >
      {children}

      {/* Overlay when dragging over */}
      {isOver && renderOverlay && renderOverlay(isOver && isValidTarget)}
    </div>
  );
}

/**
 * Simple drop zone for projects to receive agents
 */
interface ProjectDropZoneProps {
  projectId: string;
  projectName?: string;
  children?: ReactNode;
  className?: string;
}

export function ProjectDropZone({
  projectId,
  projectName,
  children,
  className,
}: ProjectDropZoneProps) {
  return (
    <DroppableZone
      id={`project-${projectId}`}
      type="project"
      data={{ projectId, projectName }}
      className={className}
    >
      {children}
    </DroppableZone>
  );
}

/**
 * Simple drop zone for agents to receive projects
 */
interface AgentDropZoneProps {
  agentId: string;
  agent?: { agentId: string; status: string; isAvailable: boolean };
  children?: ReactNode;
  className?: string;
}

export function AgentDropZone({
  agentId,
  agent,
  children,
  className,
}: AgentDropZoneProps) {
  // Disable if agent is not available
  const isDisabled = agent ? !agent.isAvailable || agent.status !== 'available' : false;

  return (
    <DroppableZone
      id={`agent-${agentId}`}
      type="agent"
      data={{ agentId, agent }}
      disabled={isDisabled}
      className={className}
    >
      {children}
    </DroppableZone>
  );
}

/**
 * Empty state drop zone panel
 */
interface EmptyDropZoneProps {
  /** Text to show when not hovering */
  idleText?: string;
  /** Text to show when hovering with valid drop */
  hoverText?: string;
  /** Icon component */
  icon?: ReactNode;
  /** Additional CSS classes */
  className?: string;
}

export function EmptyDropZone({
  idleText = 'Drop here to assign',
  hoverText = 'Release to assign',
  icon,
  className,
}: EmptyDropZoneProps) {
  return (
    <div
      className={cn(
        'border-2 border-dashed rounded-lg p-6 text-center text-muted-foreground transition-colors',
        'hover:border-primary/50 hover:bg-primary/5',
        className
      )}
    >
      {icon && <div className="flex justify-center mb-2">{icon}</div>}
      <p className="text-sm">{idleText}</p>
      <p className="text-xs mt-1 opacity-60">{hoverText}</p>
    </div>
  );
}
