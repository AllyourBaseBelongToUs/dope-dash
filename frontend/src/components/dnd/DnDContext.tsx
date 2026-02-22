'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  UniqueIdentifier,
} from '@dnd-kit/core';
import type { AgentPoolAgent, Project } from '@/types';

interface DnDContextValue {
  activeAgent: AgentPoolAgent | null;
  activeProject: Project | null;
  isDragging: boolean;
  dragType: 'agent' | 'project' | null;
}

const DnDContextValue = createContext<DnDContextValue>({
  activeAgent: null,
  activeProject: null,
  isDragging: false,
  dragType: null,
});

export function useDnD() {
  return useContext(DnDContextValue);
}

interface AssignmentDnDContextProps {
  children: ReactNode;
  /** Called when an agent is assigned to a project */
  onAssign: (agentId: string, projectId: string) => Promise<void>;
  /** Optional callback when drag starts */
  onDragStart?: (type: 'agent' | 'project', id: UniqueIdentifier) => void;
  /** Optional callback when drag ends */
  onDragEnd?: (success: boolean) => void;
}

export function AssignmentDnDContext({
  children,
  onAssign,
  onDragStart,
  onDragEnd,
}: AssignmentDnDContextProps) {
  const [activeAgent, setActiveAgent] = useState<AgentPoolAgent | null>(null);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Require 8px movement before starting drag
      },
    }),
    useSensor(KeyboardSensor)
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const data = active.data.current;

      if (data?.type === 'agent') {
        setActiveAgent(data.agent as AgentPoolAgent);
        setActiveProject(null);
        setIsDragging(true);
        onDragStart?.('agent', active.id);
      } else if (data?.type === 'project') {
        setActiveProject(data.project as Project);
        setActiveAgent(null);
        setIsDragging(true);
        onDragStart?.('project', active.id);
      }
    },
    [onDragStart]
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;

      // Reset state
      const wasAgent = !!activeAgent;
      setActiveAgent(null);
      setActiveProject(null);
      setIsDragging(false);

      if (!over) {
        onDragEnd?.(false);
        return;
      }

      const activeData = active.data.current;
      const overData = over.data.current;

      let success = false;

      try {
        // Agent dropped on Project
        if (activeData?.type === 'agent' && overData?.type === 'project') {
          await onAssign(activeData.agent.agentId, overData.projectId);
          success = true;
        }

        // Project dropped on Agent (reverse direction)
        if (activeData?.type === 'project' && overData?.type === 'agent') {
          await onAssign(overData.agent.agentId, activeData.projectId);
          success = true;
        }
      } catch (error) {
        console.error('Assignment failed:', error);
        success = false;
      }

      onDragEnd?.(success);
    },
    [activeAgent, onAssign, onDragEnd]
  );

  return (
    <DnDContextValue.Provider
      value={{
        activeAgent,
        activeProject,
        isDragging,
        dragType: activeAgent ? 'agent' : activeProject ? 'project' : null,
      }}
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {children}

        {/* Drag Overlay - shows what's being dragged */}
        <DragOverlay dropAnimation={null}>
          {activeAgent && (
            <div className="px-4 py-3 bg-primary text-primary-foreground rounded-lg shadow-lg font-medium text-sm">
              <div className="flex items-center gap-2">
                <span>{activeAgent.agentId}</span>
                <span className="text-xs opacity-80">({activeAgent.agentType})</span>
              </div>
            </div>
          )}
          {activeProject && (
            <div className="px-4 py-3 bg-primary text-primary-foreground rounded-lg shadow-lg font-medium text-sm">
              <div className="flex items-center gap-2">
                <span>{activeProject.name}</span>
                <span className="text-xs opacity-80">({activeProject.status})</span>
              </div>
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </DnDContextValue.Provider>
  );
}

/**
 * Hook to check if a drop zone is valid for the current drag
 */
export function useDropValidation() {
  const { dragType, activeAgent, activeProject } = useDnD();

  const isValidDrop = useCallback(
    (dropType: 'agent' | 'project'): boolean => {
      // Agent can only be dropped on project
      if (dragType === 'agent' && dropType === 'project') {
        return true;
      }
      // Project can only be dropped on agent
      if (dragType === 'project' && dropType === 'agent') {
        return true;
      }
      return false;
    },
    [dragType]
  );

  const canAcceptAgent = useCallback(
    (agent: AgentPoolAgent): boolean => {
      // Check if agent is available for assignment
      return agent.isAvailable && agent.status === 'available';
    },
    []
  );

  return {
    isValidDrop,
    canAcceptAgent,
    activeAgent,
    activeProject,
    dragType,
  };
}
