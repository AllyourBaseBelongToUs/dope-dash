'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useAgentPoolStore } from '@/store/agentPoolStore';
import { usePortfolioStore } from '@/store/portfolioStore';
import { AppShell } from '@/components/AppShell';
import { ResizableSplitPanel } from '@/components/ui/resizable-panel';
import { AgentCard } from '@/components/agent-pool/AgentCard';
import { ProjectSessionPanel, type ProjectSessionData } from '@/components/portfolio/ProjectSessionPanel';
import { AssignmentDnDContext } from '@/components/dnd';
import { Server, FolderKanban, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { getAgentColor } from '@/lib/agentColors';

export default function AssignmentPage() {
  const {
    agents,
    assignAgent,
    fetchAgents,
    isLoading: agentsLoading,
    error: agentsError,
  } = useAgentPoolStore();

  const {
    projects,
    fetchProjects,
    isLoading: projectsLoading,
    error: projectsError,
  } = usePortfolioStore();

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load initial data
  useEffect(() => {
    fetchAgents();
    fetchProjects();
  }, [fetchAgents, fetchProjects]);

  // Create project session data from projects (memoized for performance)
  const projectSessionData: ProjectSessionData[] = useMemo(() =>
    projects.map(project => {
      // Find linked agent for this project
      const linkedAgent = agents.find(a => a.currentProjectId === project.id || a.assignedProject?.id === project.id);

      return {
        id: project.id,
        name: project.name,
        path: project.metadata?.['working_dir'] as string || `/path/to/${project.name}`,
        completion: Math.round(project.progress * 100),
        linkedAgentId: linkedAgent?.agentId,
        linkedAgentName: linkedAgent?.agentId,
        linkedAgentColor: linkedAgent ? getAgentColor(linkedAgent.agentId) : undefined,
        tokensUsed: project.metadata?.['total_tokens'] as number | undefined,
        lastActivity: project.lastActivityAt,
        status: project.status === 'running' ? 'active' :
                 project.status === 'idle' ? 'idle' :
                 project.status === 'completed' ? 'completed' : 'error',
      };
    }), [projects, agents]
  );

  const handleAssign = useCallback(async (agentId: string, projectId: string) => {
    try {
      const response = await assignAgent({
        projectId,
        preferredAgentId: agentId,
        capabilities: [],
      });

      if (response.success) {
        toast({
          title: 'Agent assigned',
          description: `Agent ${agentId} assigned to project successfully`,
        });
        // Refresh to show updated state
        await fetchAgents();
        await fetchProjects();
      } else {
        toast({
          variant: 'destructive',
          title: 'Assignment failed',
          description: response.message || 'Failed to assign agent',
        });
      }
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Assignment failed',
        description: err instanceof Error ? err.message : 'Failed to assign agent',
      });
    }
  }, [assignAgent, fetchAgents, fetchProjects]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchAgents(), fetchProjects()]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchAgents, fetchProjects]);

  const handleAgentSelect = useCallback((agent: typeof agents[0]) => {
    setSelectedAgent(agent.agentId);
    setSelectedProject(null);
  }, []);

  const handleProjectClick = useCallback((projectId: string) => {
    setSelectedProject(projectId);
    setSelectedAgent(null);
  }, []);

  return (
    <AssignmentDnDContext onAssign={handleAssign}>
      <AppShell
        title="Assignment Center"
        subtitle="Assign agents to projects with drag-and-drop"
        icon={<Server className="h-5 w-5 text-primary" />}
        sessionCount={agents.filter(a => a.status === 'busy').length}
        agentCount={agents.length}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing || agentsLoading || projectsLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      >
        {(agentsError || projectsError) && (
          <div className="mb-4 border border-red-500/50 bg-red-500/10 rounded-lg p-4">
            <p className="text-red-500 text-sm">
              {agentsError || projectsError || 'Failed to load data'}
            </p>
          </div>
        )}

        <ResizableSplitPanel
          storageKey="assignment-panel-split"
          defaultLeftWidth={40}
          minLeftWidth={25}
          maxLeftWidth={60}
          className="h-[calc(100vh-12rem)]"
          left={
            <div className="h-full overflow-y-auto p-4 border-r bg-muted/20">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Server className="h-5 w-5 text-primary" />
                  Agents ({agents.length})
                </h2>
              </div>
              {agentsLoading ? (
                <div className="text-center py-8" style={{ color: 'var(--font-color)' }}>
                  Loading agents...
                </div>
              ) : agents.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--font-color)' }}>
                  No agents registered. Add agents to get started.
                </div>
              ) : (
                <div className="space-y-4">
                  {agents.map(agent => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      draggable={agent.status === 'available' || agent.status === 'busy'}
                      onSelect={handleAgentSelect}
                    />
                  ))}
                </div>
              )}
            </div>
          }
          right={
            <div className="h-full overflow-y-auto p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <FolderKanban className="h-5 w-5 text-primary" />
                  Projects ({projects.length})
                </h2>
              </div>
              {projectsLoading ? (
                <div className="text-center py-8" style={{ color: 'var(--font-color)' }}>
                  Loading projects...
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--font-color)' }}>
                  No projects found. Create a project to get started.
                </div>
              ) : (
                <div className="space-y-4">
                  {projectSessionData.map(project => (
                    <ProjectSessionPanel
                      key={project.id}
                      project={project}
                      isHovered={selectedProject === project.id}
                      onClick={() => handleProjectClick(project.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          }
        />
      </AppShell>
    </AssignmentDnDContext>
  );
}
