'use client';

import { useState, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { AgentSearch } from './AgentSearch';
import { AssignmentDnDContext } from '@/components/dnd';
import { DroppableZone, EmptyDropZone } from '@/components/dnd/DroppableZone';
import { Search, GripVertical, Loader2, Check, AlertCircle, UserPlus } from 'lucide-react';
import { useAgentPoolStore } from '@/store/agentPoolStore';
import { cn } from '@/lib/utils';
import type { AgentPoolAgent } from '@/types';

interface AssignAgentDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** The project ID to assign an agent to */
  projectId: string;
  /** The project name for display */
  projectName: string;
  /** Callback when assignment is made */
  onAssign: (agentId: string) => Promise<void>;
  /** Optional pre-selected agent type filter */
  preferredAgentType?: string;
  /** Optional required capabilities */
  requiredCapabilities?: string[];
}

export function AssignAgentDialog({
  open,
  onOpenChange,
  projectId,
  projectName,
  onAssign,
  preferredAgentType,
  requiredCapabilities = [],
}: AssignAgentDialogProps) {
  const { agents, assignAgent, isLoading } = useAgentPoolStore();
  const [selectedAgent, setSelectedAgent] = useState<AgentPoolAgent | null>(null);
  const [isAssigning, setIsAssigning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('search');

  // Filter function for agent search
  const filterFn = useCallback(
    (agent: AgentPoolAgent) => {
      // Only show available agents
      if (!agent.isAvailable || agent.status !== 'available') {
        return false;
      }

      // Filter by preferred agent type if specified
      if (preferredAgentType && agent.agentType !== preferredAgentType) {
        return false;
      }

      // Filter by required capabilities
      if (requiredCapabilities.length > 0) {
        const hasAllCapabilities = requiredCapabilities.every((cap) =>
          agent.capabilities.includes(cap)
        );
        if (!hasAllCapabilities) {
          return false;
        }
      }

      return true;
    },
    [preferredAgentType, requiredCapabilities]
  );

  // Handle assignment
  const handleAssign = async () => {
    if (!selectedAgent) return;

    setIsAssigning(true);
    setError(null);

    try {
      await onAssign(selectedAgent.agentId);
      onOpenChange(false);
      setSelectedAgent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign agent');
    } finally {
      setIsAssigning(false);
    }
  };

  // Handle drag-and-drop assignment
  const handleDnDAssign = useCallback(
    async (agentId: string, droppedProjectId: string) => {
      if (droppedProjectId !== projectId) return;

      setIsAssigning(true);
      setError(null);

      try {
        await onAssign(agentId);
        onOpenChange(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to assign agent');
      } finally {
        setIsAssigning(false);
      }
    },
    [projectId, onAssign, onOpenChange]
  );

  // Reset state when dialog closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedAgent(null);
      setError(null);
      setActiveTab('search');
    }
    onOpenChange(newOpen);
  };

  // Count available agents
  const availableAgents = agents.filter(filterFn);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Assign Agent to Project
          </DialogTitle>
          <DialogDescription>
            Assign an agent to work on{' '}
            <span className="font-medium text-foreground">{projectName}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Project Info */}
        <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg mb-4">
          <Badge variant="outline">Project ID</Badge>
          <code className="text-xs text-muted-foreground">{projectId}</code>
        </div>

        {/* Required Capabilities */}
        {requiredCapabilities.length > 0 && (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm text-muted-foreground">Required:</span>
            {requiredCapabilities.map((cap) => (
              <Badge key={cap} variant="secondary" className="text-xs">
                {cap}
              </Badge>
            ))}
          </div>
        )}

        {/* Assignment Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="search" className="gap-2">
              <Search className="h-4 w-4" />
              Search
            </TabsTrigger>
            <TabsTrigger value="drag" className="gap-2">
              <GripVertical className="h-4 w-4" />
              Drag & Drop
            </TabsTrigger>
          </TabsList>

          {/* Search Tab */}
          <TabsContent value="search" className="mt-4">
            <AgentSearch
              agents={agents}
              onSelect={setSelectedAgent}
              filterFn={filterFn}
              placeholder="Search available agents..."
              availableOnly={true}
              selectedAgentId={selectedAgent?.agentId}
              isLoading={isLoading}
              error={error}
            />

            {/* Available count */}
            <div className="text-xs text-muted-foreground mt-2">
              {availableAgents.length} available agent{availableAgents.length !== 1 ? 's' : ''}
            </div>
          </TabsContent>

          {/* Drag & Drop Tab */}
          <TabsContent value="drag" className="mt-4">
            <AssignmentDnDContext onAssign={handleDnDAssign}>
              <div className="space-y-4">
                {/* Drop Zone */}
                <DroppableZone
                  id={`project-drop-${projectId}`}
                  type="agent"
                  data={{ projectId, projectName }}
                >
                  {selectedAgent ? (
                    <div className="p-4 border rounded-lg bg-primary/5 text-center">
                      <div className="font-medium">{selectedAgent.agentId}</div>
                      <div className="text-sm text-muted-foreground">
                        {selectedAgent.agentType} | Load: {selectedAgent.currentLoad}/
                        {selectedAgent.maxCapacity}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-2"
                        onClick={() => setSelectedAgent(null)}
                      >
                        Clear
                      </Button>
                    </div>
                  ) : (
                    <EmptyDropZone
                      idleText="Drag an agent card here to assign"
                      hoverText="Release to assign this agent"
                      icon={<GripVertical className="h-8 w-8 text-muted-foreground" />}
                    />
                  )}
                </DroppableZone>

                {/* Instructions */}
                <div className="text-sm text-muted-foreground text-center">
                  <p>Drag an agent from the Agent Pool to this area</p>
                  <p className="text-xs mt-1">Only available agents can be assigned</p>
                </div>
              </div>
            </AssignmentDnDContext>
          </TabsContent>
        </Tabs>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-500 p-3 bg-red-500/10 rounded-lg">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAssign} disabled={!selectedAgent || isAssigning}>
            {isAssigning ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Assigning...
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Assign Agent
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Quick assign button component for embedding in other UIs
 */
interface QuickAssignButtonProps {
  projectId: string;
  projectName: string;
  preferredAgentType?: string;
  requiredCapabilities?: string[];
  onAssign: (agentId: string) => Promise<void>;
  className?: string;
}

export function QuickAssignButton({
  projectId,
  projectName,
  preferredAgentType,
  requiredCapabilities,
  onAssign,
  className,
}: QuickAssignButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className={cn('gap-2', className)}
        onClick={() => setDialogOpen(true)}
      >
        <UserPlus className="h-4 w-4" />
        Assign Agent
      </Button>

      <AssignAgentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        projectId={projectId}
        projectName={projectName}
        preferredAgentType={preferredAgentType}
        requiredCapabilities={requiredCapabilities}
        onAssign={onAssign}
      />
    </>
  );
}
