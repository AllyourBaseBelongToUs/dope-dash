'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePortfolioStore } from '@/store/portfolioStore';
import { useAgentPoolStore } from '@/store/agentPoolStore';
import { AppShell } from '@/components/AppShell';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { PortfolioFilters } from '@/components/portfolio/PortfolioFilters';
import { ProjectCard } from '@/components/portfolio/ProjectCard';
import { ProjectDetailDialog } from '@/components/portfolio/ProjectDetailDialog';
import { CreateProjectDialog } from '@/components/portfolio/CreateProjectDialog';
import { BulkActionBar } from '@/components/portfolio/BulkActionBar';
import { BulkOperationResults } from '@/components/portfolio/BulkOperationResults';
import { AssignmentDnDContext } from '@/components/dnd';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from '@/components/ui/use-toast';
import {
  FolderKanban,
  Plus,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import type { Project, ProjectStatus, ProjectPriority } from '@/types';

// Use a subset of ProjectControlAction that matches what BulkActionBar can produce
type BulkActionResultAction = 'pause' | 'resume' | 'stop';

interface BulkOperationResult {
  action: BulkActionResultAction;
  total_requested: number;
  successful: number;
  failed: number;
  total_agents_affected: number;
}

export default function PortfolioPage() {
  const {
    projects,
    selectedProject,
    summary,
    isLoading,
    error,
    statusFilter,
    priorityFilter,
    searchQuery,
    total,
    limit,
    offset,
    selectedProjectIds,
    isAllSelected,
    fetchProjects,
    fetchProject,
    fetchSummary,
    setStatusFilter,
    setPriorityFilter,
    setSearchQuery,
    setOffset,
    syncProject,
    deleteProject,
    refresh,
    toggleProjectSelection,
    selectAllProjects,
    deselectAllProjects,
  } = usePortfolioStore();

  const { assignAgent } = useAgentPoolStore();

  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [projectToSync, setProjectToSync] = useState<string | null>(null);
  const [bulkOperationResult, setBulkOperationResult] = useState<BulkOperationResult | null>(null);
  const [isBulkMode, setIsBulkMode] = useState(false);

  // Handle drag-and-drop agent assignment
  const handleAgentAssign = useCallback(async (agentId: string, projectId: string) => {
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
        await fetchProjects();
        await fetchSummary();
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
  }, [assignAgent, fetchProjects, fetchSummary]);

  // Load initial data
  useEffect(() => {
    fetchProjects();
    fetchSummary();
  }, []);

  // Auto-refresh interval for running projects
  useEffect(() => {
    const hasRunningProjects = projects.some((p) => p.status === 'running');
    if (hasRunningProjects) {
      const interval = setInterval(() => {
        fetchProjects();
        fetchSummary();
      }, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [projects]);

  const handleViewProject = async (project: Project) => {
    await fetchProject(project.id);
    setDetailDialogOpen(true);
  };

  const handleSyncProject = async (projectId: string) => {
    setProjectToSync(projectId);
    try {
      await syncProject(projectId);
      if (selectedProject?.id === projectId) {
        await fetchProject(projectId);
      }
    } finally {
      setProjectToSync(null);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (confirm('Are you sure you want to delete this project?')) {
      await deleteProject(projectId);
      if (selectedProject?.id === projectId) {
        setDetailDialogOpen(false);
      }
    }
  };

  const handleControlApplied = async () => {
    // Refresh the project list and summary after a control action
    await fetchProjects();
    await fetchSummary();
    // Refresh the selected project if dialog is open
    if (selectedProject) {
      await fetchProject(selectedProject.id);
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
    setPriorityFilter('all');
    setOffset(0);
  };

  return (
    <AssignmentDnDContext onAssign={handleAgentAssign}>
      <AppShell
        title="Portfolio"
        subtitle="Mission Control - Project Overview"
        icon={<FolderKanban className="h-5 w-5 text-primary" />}
        sessionCount={projects.filter(p => p.status === 'running').length}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refresh()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant={isBulkMode ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setIsBulkMode(!isBulkMode);
                if (isBulkMode) {
                  deselectAllProjects();
                }
              }}
            >
              {isBulkMode ? 'Exit Bulk Mode' : 'Bulk Select'}
            </Button>
            <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </>
        }
      >
        {/* Error State */}
        {error && (
          <div className="mb-6 border border-red-500/50 bg-red-500/10 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-500">Error</p>
              <p className="text-sm text-red-500/80">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refresh()}
              className="ml-auto"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Summary Section */}
        <section className="mb-8">
          <PortfolioSummary summary={summary} isLoading={isLoading && !summary} />
        </section>

        {/* Filters Section */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <PortfolioFilters
              searchQuery={searchQuery}
              statusFilter={statusFilter}
              priorityFilter={priorityFilter}
              onSearchChange={setSearchQuery}
              onStatusChange={setStatusFilter}
              onPriorityChange={setPriorityFilter}
              onClearFilters={handleClearFilters}
              totalProjects={total}
              filteredCount={projects.length}
            />
            {isBulkMode && projects.length > 0 && (
              <div className="flex items-center gap-2 ml-4">
                <Checkbox
                  checked={isAllSelected}
                  onChange={(e) => {
                    if (e.target.checked) {
                      selectAllProjects();
                    } else {
                      deselectAllProjects();
                    }
                  }}
                  className="shrink-0"
                />
                <span className="text-sm" style={{ color: 'var(--font-color)' }}>
                  {selectedProjectIds.size > 0
                    ? `${selectedProjectIds.size} selected`
                    : 'Select all'}
                </span>
              </div>
            )}
          </div>
        </section>

        {/* Projects Grid */}
        <section>
          {isLoading && projects.length === 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="border border-border rounded-lg p-6 animate-pulse"
                >
                  <div className="h-6 bg-muted rounded w-3/4 mb-4" />
                  <div className="h-4 bg-muted rounded w-full mb-2" />
                  <div className="h-4 bg-muted rounded w-1/2 mb-4" />
                  <div className="h-2 bg-muted rounded w-full mb-2" />
                  <div className="h-2 bg-muted rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : projects.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onView={handleViewProject}
                  onSync={handleSyncProject}
                  onDelete={handleDeleteProject}
                  isUpdating={projectToSync === project.id}
                  onControlApplied={handleControlApplied}
                  isSelected={selectedProjectIds.has(project.id)}
                  onToggleSelection={toggleProjectSelection}
                  isBulkMode={isBulkMode}
                />
              ))}
            </div>
          ) : (
            <div className="border border-dashed border-border rounded-lg p-12 text-center">
              <FolderKanban className="h-12 w-12 mx-auto mb-4" style={{ color: 'var(--chart-overlay-color)' }} />
              <h3 className="text-lg font-medium mb-2">No projects found</h3>
              <p className="mb-4" style={{ color: 'var(--font-color)' }}>
                {hasActiveFilters(searchQuery, statusFilter, priorityFilter)
                  ? 'Try adjusting your filters to see more results.'
                  : 'Get started by creating your first project.'}
              </p>
              {!hasActiveFilters(searchQuery, statusFilter, priorityFilter) && (
                <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              )}
            </div>
          )}
        </section>

        {/* Load More */}
        {projects.length < total && (
          <div className="mt-8 text-center">
            <Button
              variant="outline"
              onClick={() => {
                setOffset(offset + limit);
              }}
            >
              Load More ({total - projects.length} remaining)
            </Button>
          </div>
        )}
      </AppShell>

      {/* Detail Dialog */}
      <ProjectDetailDialog
        project={selectedProject}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        onSync={async () => {
          if (selectedProject) {
            await handleSyncProject(selectedProject.id);
          }
        }}
        onDelete={async () => {
          if (selectedProject) {
            await handleDeleteProject(selectedProject.id);
          }
        }}
        isUpdating={projectToSync === selectedProject?.id}
        onControlApplied={handleControlApplied}
      />

      {/* Bulk Action Bar */}
      {isBulkMode && selectedProjectIds.size > 0 && (
        <BulkActionBar
          selectedCount={selectedProjectIds.size}
          onDeselectAll={deselectAllProjects}
          onOperationComplete={(result) => {
            // Cast to subset type since BulkActionBar only produces pause|resume|stop
            setBulkOperationResult(result as BulkOperationResult);
          }}
        />
      )}

      {/* Bulk Operation Results */}
      {bulkOperationResult && (
        <BulkOperationResults
          action={bulkOperationResult.action}
          totalRequested={bulkOperationResult.total_requested}
          successful={bulkOperationResult.successful}
          failed={bulkOperationResult.failed}
          totalAgentsAffected={bulkOperationResult.total_agents_affected}
          results={[]}
          timestamp={new Date()}
          onClose={() => setBulkOperationResult(null)}
        />
      )}

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </AssignmentDnDContext>
  );
}

function hasActiveFilters(searchQuery: string, statusFilter: ProjectStatus | 'all', priorityFilter: ProjectPriority | 'all') {
  return searchQuery.trim() !== '' || statusFilter !== 'all' || priorityFilter !== 'all';
}
