'use client';

import { useState, useEffect } from 'react';
import { usePortfolioStore } from '@/store/portfolioStore';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { PortfolioFilters } from '@/components/portfolio/PortfolioFilters';
import { ProjectCard } from '@/components/portfolio/ProjectCard';
import { ProjectDetailDialog } from '@/components/portfolio/ProjectDetailDialog';
import { BulkActionBar } from '@/components/portfolio/BulkActionBar';
import { BulkOperationResults } from '@/components/portfolio/BulkOperationResults';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
    selectedProjectIds,
    isAllSelected,
    fetchProjects,
    fetchProject,
    fetchSummary,
    setStatusFilter,
    setPriorityFilter,
    setSearchQuery,
    syncProject,
    deleteProject,
    refresh,
    toggleProjectSelection,
    selectAllProjects,
    deselectAllProjects,
  } = usePortfolioStore();

  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [projectToSync, setProjectToSync] = useState<string | null>(null);
  const [bulkOperationResult, setBulkOperationResult] = useState<BulkOperationResult | null>(null);
  const [isBulkMode, setIsBulkMode] = useState(false);

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
  };

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <FolderKanban className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Portfolio</h1>
                <p className="text-xs text-muted-foreground">Mission Control - Project Overview</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
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
                {isBulkMode ? (
                  <>Exit Bulk Mode</>
                ) : (
                  <>Bulk Select</>
                )}
              </Button>
              <Button size="sm" onClick={() => {/* TODO: Open create project dialog */}}>
                <Plus className="h-4 w-4 mr-2" />
                New Project
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
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
                <span className="text-sm text-muted-foreground">
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
              <FolderKanban className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No projects found</h3>
              <p className="text-muted-foreground mb-4">
                {hasActiveFilters()
                  ? 'Try adjusting your filters to see more results.'
                  : 'Get started by creating your first project.'}
              </p>
              {!hasActiveFilters() && (
                <Button size="sm" onClick={() => {/* TODO: Open create project dialog */}}>
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
                // TODO: Implement pagination
              }}
            >
              Load More ({total - projects.length} remaining)
            </Button>
          </div>
        )}
      </div>

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
    </main>
  );
}

function hasActiveFilters() {
  // This is a helper function - in real implementation you'd check the store
  return false;
}
