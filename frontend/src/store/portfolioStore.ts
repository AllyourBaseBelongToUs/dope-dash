import { create } from 'zustand';
import type {
  Project,
  ProjectSummary,
  ProjectDetail,
  ProjectStatus,
  ProjectPriority,
  ProjectControlHistoryEntry,
  ProjectControlAction,
} from '@/types';
import { getPortfolioService } from '@/services/portfolioService';

interface BulkOperationResult {
  projectId: string;
  projectName: string;
  success: boolean;
  message: string;
  agentsAffected: number;
  error?: string;
}

interface PortfolioState {
  // State
  projects: Project[];
  selectedProject: ProjectDetail | null;
  summary: ProjectSummary | null;
  isLoading: boolean;
  error: string | null;

  // Filters
  statusFilter: ProjectStatus | 'all';
  priorityFilter: ProjectPriority | 'all';
  searchQuery: string;

  // Pagination
  total: number;
  limit: number;
  offset: number;

  // Bulk selection
  selectedProjectIds: Set<string>;
  isAllSelected: boolean;

  // Actions
  setProjects: (projects: Project[]) => void;
  setSelectedProject: (project: ProjectDetail | null) => void;
  setSummary: (summary: ProjectSummary) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setStatusFilter: (status: ProjectStatus | 'all') => void;
  setPriorityFilter: (priority: ProjectPriority | 'all') => void;
  setSearchQuery: (query: string) => void;
  setOffset: (offset: number) => void;

  // API Actions
  fetchProjects: () => Promise<void>;
  fetchProject: (projectId: string) => Promise<void>;
  fetchSummary: () => Promise<void>;
  createProject: (data: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  updateProject: (projectId: string, data: Partial<Project>) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  syncProject: (projectId: string) => Promise<void>;
  refresh: () => Promise<void>;

  // Control Actions
  pauseProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  resumeProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  skipProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  stopProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  retryProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  restartProject: (projectId: string) => Promise<{ message: string; agentsAffected: number }>;
  fetchProjectControls: (projectId: string, limit?: number) => Promise<ProjectControlHistoryEntry[]>;

  // Bulk Selection Actions
  toggleProjectSelection: (projectId: string) => void;
  selectAllProjects: () => void;
  deselectAllProjects: () => void;
  clearSelection: () => void;
  getSelectedProjectIds: () => string[];
  getSelectedProjectsCount: () => number;

  // Bulk Control Actions
  bulkPauseProjects: () => Promise<{
    action: ProjectControlAction;
    total_requested: number;
    successful: number;
    failed: number;
    results: BulkOperationResult[];
    total_agents_affected: number;
  }>;
  bulkResumeProjects: () => Promise<{
    action: ProjectControlAction;
    total_requested: number;
    successful: number;
    failed: number;
    results: BulkOperationResult[];
    total_agents_affected: number;
  }>;
  bulkStopProjects: () => Promise<{
    action: ProjectControlAction;
    total_requested: number;
    successful: number;
    failed: number;
    results: BulkOperationResult[];
    total_agents_affected: number;
  }>;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  // Initial state
  projects: [],
  selectedProject: null,
  summary: null,
  isLoading: false,
  error: null,
  statusFilter: 'all',
  priorityFilter: 'all',
  searchQuery: '',
  total: 0,
  limit: 100,
  offset: 0,
  selectedProjectIds: new Set<string>(),
  isAllSelected: false,
  limit: 100,
  offset: 0,

  // Setters
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (project) => set({ selectedProject: project }),
  setSummary: (summary) => set({ summary }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setStatusFilter: (statusFilter) => {
    set({ statusFilter, offset: 0 });
    get().fetchProjects();
  },
  setPriorityFilter: (priorityFilter) => {
    set({ priorityFilter, offset: 0 });
    get().fetchProjects();
  },
  setSearchQuery: (searchQuery) => {
    set({ searchQuery, offset: 0 });
    get().fetchProjects();
  },
  setOffset: (offset) => {
    set({ offset });
    get().fetchProjects();
  },

  // API Actions
  fetchProjects: async () => {
    const { statusFilter, priorityFilter, searchQuery, limit, offset } = get();
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const params: {
        status?: ProjectStatus;
        priority?: ProjectPriority;
        search?: string;
        limit: number;
        offset: number;
      } = { limit, offset };

      if (statusFilter !== 'all') params.status = statusFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (searchQuery) params.search = searchQuery;

      const response = await service.getProjects(params);
      set({
        projects: response.projects,
        total: response.total,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch projects',
        isLoading: false,
      });
    }
  },

  fetchProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const project = await service.getProject(projectId);
      set({
        selectedProject: project,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch project',
        isLoading: false,
      });
    }
  },

  fetchSummary: async () => {
    try {
      const service = getPortfolioService();
      const summary = await service.getSummary();
      set({ summary });
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  },

  createProject: async (data) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      await service.createProject({
        name: data.name,
        status: data.status,
        priority: data.priority,
        description: data.description,
        progress: data.progress,
        totalSpecs: data.totalSpecs,
        completedSpecs: data.completedSpecs,
        activeAgents: data.activeAgents,
        metadata: data.metadata,
      });
      await get().fetchProjects();
      await get().fetchSummary();
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create project',
        isLoading: false,
      });
      throw error;
    }
  },

  updateProject: async (projectId, data) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const updated = await service.updateProject(projectId, {
        status: data.status,
        priority: data.priority,
        description: data.description,
        progress: data.progress,
        totalSpecs: data.totalSpecs,
        completedSpecs: data.completedSpecs,
        activeAgents: data.activeAgents,
        lastActivityAt: data.lastActivityAt,
        metadata: data.metadata,
      });

      // Update projects list
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === projectId ? updated : p
        ),
        // Update selected project if it's the same one
        selectedProject:
          state.selectedProject?.id === projectId
            ? { ...updated, stats: state.selectedProject.stats, recentSessions: state.selectedProject.recentSessions }
            : state.selectedProject,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update project',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteProject: async (projectId) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      await service.deleteProject(projectId);

      // Remove from projects list
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== projectId),
        selectedProject: state.selectedProject?.id === projectId ? null : state.selectedProject,
        isLoading: false,
      }));

      // Refresh summary
      await get().fetchSummary();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete project',
        isLoading: false,
      });
      throw error;
    }
  },

  syncProject: async (projectId) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const updated = await service.syncProject(projectId);

      // Update projects list
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === projectId ? updated : p
        ),
        selectedProject:
          state.selectedProject?.id === projectId
            ? { ...updated, stats: state.selectedProject.stats, recentSessions: state.selectedProject.recentSessions }
            : state.selectedProject,
        isLoading: false,
      }));

      // Refresh summary
      await get().fetchSummary();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to sync project',
        isLoading: false,
      });
      throw error;
    }
  },

  refresh: async () => {
    await Promise.all([
      get().fetchProjects(),
      get().fetchSummary(),
    ]);
  },

  // Control Actions
  pauseProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.pauseProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to pause project',
        isLoading: false,
      });
      throw error;
    }
  },

  resumeProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.resumeProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to resume project',
        isLoading: false,
      });
      throw error;
    }
  },

  skipProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.skipProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to skip project',
        isLoading: false,
      });
      throw error;
    }
  },

  stopProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.stopProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to stop project',
        isLoading: false,
      });
      throw error;
    }
  },

  retryProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.retryProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to retry project',
        isLoading: false,
      });
      throw error;
    }
  },

  restartProject: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.restartProject(projectId);

      // Refresh project data
      await get().fetchProject(projectId);

      set({ isLoading: false });
      return { message: result.message, agentsAffected: result.agents_affected };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to restart project',
        isLoading: false,
      });
      throw error;
    }
  },

  fetchProjectControls: async (projectId: string, limit: number = 50) => {
    try {
      const service = getPortfolioService();
      const response = await service.getProjectControls(projectId, { limit });
      return response.controls;
    } catch (error) {
      console.error('Failed to fetch project controls:', error);
      return [];
    }
  },

  // Bulk Selection Actions
  toggleProjectSelection: (projectId: string) => {
    const currentSelection = get().selectedProjectIds;
    const newSelection = new Set(currentSelection);

    if (newSelection.has(projectId)) {
      newSelection.delete(projectId);
    } else {
      newSelection.add(projectId);
    }

    const projects = get().projects;
    set({
      selectedProjectIds: newSelection,
      isAllSelected: newSelection.size === projects.length && projects.length > 0,
    });
  },

  selectAllProjects: () => {
    const projects = get().projects;
    const allIds = new Set(projects.map((p) => p.id));
    set({
      selectedProjectIds: allIds,
      isAllSelected: true,
    });
  },

  deselectAllProjects: () => {
    set({
      selectedProjectIds: new Set(),
      isAllSelected: false,
    });
  },

  clearSelection: () => {
    set({
      selectedProjectIds: new Set(),
      isAllSelected: false,
    });
  },

  getSelectedProjectIds: () => {
    return Array.from(get().selectedProjectIds);
  },

  getSelectedProjectsCount: () => {
    return get().selectedProjectIds.size;
  },

  // Bulk Control Actions
  bulkPauseProjects: async () => {
    const projectIds = get().getSelectedProjectIds();
    if (projectIds.length === 0) {
      throw new Error('No projects selected');
    }

    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.bulkPauseProjects(projectIds);

      // Refresh project data
      await get().fetchProjects();
      await get().fetchSummary();

      // Clear selection after successful operation
      get().clearSelection();

      set({ isLoading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to pause projects',
        isLoading: false,
      });
      throw error;
    }
  },

  bulkResumeProjects: async () => {
    const projectIds = get().getSelectedProjectIds();
    if (projectIds.length === 0) {
      throw new Error('No projects selected');
    }

    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.bulkResumeProjects(projectIds);

      // Refresh project data
      await get().fetchProjects();
      await get().fetchSummary();

      // Clear selection after successful operation
      get().clearSelection();

      set({ isLoading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to resume projects',
        isLoading: false,
      });
      throw error;
    }
  },

  bulkStopProjects: async () => {
    const projectIds = get().getSelectedProjectIds();
    if (projectIds.length === 0) {
      throw new Error('No projects selected');
    }

    set({ isLoading: true, error: null });

    try {
      const service = getPortfolioService();
      const result = await service.bulkStopProjects(projectIds);

      // Refresh project data
      await get().fetchProjects();
      await get().fetchSummary();

      // Clear selection after successful operation
      get().clearSelection();

      set({ isLoading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to stop projects',
        isLoading: false,
      });
      throw error;
    }
  },
}));
