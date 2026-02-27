import type {
  Project,
  ProjectSummary,
  ProjectListResponse,
  ProjectDetail,
  ProjectStatus,
  ProjectPriority,
  ProjectControlHistoryEntry,
  ProjectControlAction,
} from '@/types';

interface ControlResponse {
  message: string;
  agents_affected: number;
}

interface BulkOperationRequest {
  project_ids: string[];
  action: ProjectControlAction;
}

interface BulkOperationResult {
  project_id: string;
  project_name: string;
  success: boolean;
  message: string;
  agents_affected: number;
  error?: string;
}

interface BulkOperationResponse {
  action: ProjectControlAction;
  total_requested: number;
  successful: number;
  failed: number;
  results: BulkOperationResult[];
  total_agents_affected: number;
}

/**
 * Portfolio Service
 * Handles fetching and managing projects in the portfolio view
 */
class PortfolioService {
  private baseUrl: string = '';

  constructor() {
    if (typeof window !== 'undefined') {
      this.baseUrl = this.getApiBaseUrl();
    }
  }

  /**
   * Get the API base URL from environment store or fallback
   */
  private getApiBaseUrl(): string {
    // Try to get from environment config
    const envConfig = localStorage.getItem('dope-dash-env-config');
    if (envConfig) {
      try {
        const config = JSON.parse(envConfig);
        return config.apiUrl || this.getDefaultApiUrl();
      } catch (e) {
        console.warn('Failed to parse env config:', e);
      }
    }
    return this.getDefaultApiUrl();
  }

  /**
   * Get default API URL based on current environment
   */
  private getDefaultApiUrl(): string {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
      }
    }
    return 'http://localhost:8000';
  }

  /**
   * Transform camelCase frontend request to snake_case API format for CREATE
   */
  private transformCreateRequest(data: {
    name: string;
    status?: ProjectStatus;
    priority?: ProjectPriority;
    description?: string;
    progress?: number;
    totalSpecs?: number;
    completedSpecs?: number;
    activeAgents?: number;
    metadata?: Record<string, unknown>;
  }): Record<string, unknown> {
    return {
      name: data.name,
      status: data.status,
      priority: data.priority,
      description: data.description,
      progress: data.progress,
      total_specs: data.totalSpecs,
      completed_specs: data.completedSpecs,
      active_agents: data.activeAgents,
      metadata: data.metadata,
    };
  }

  /**
   * Transform camelCase frontend request to snake_case API format for UPDATE
   */
  private transformUpdateRequest(data: Partial<{
    status: ProjectStatus;
    priority: ProjectPriority;
    description: string;
    progress: number;
    totalSpecs: number;
    completedSpecs: number;
    activeAgents: number;
    lastActivityAt: string;
    metadata: Record<string, unknown>;
  }>): Record<string, unknown> {
    const result: Record<string, unknown> = {};

    if (data.status !== undefined) result.status = data.status;
    if (data.priority !== undefined) result.priority = data.priority;
    if (data.description !== undefined) result.description = data.description;
    if (data.progress !== undefined) result.progress = data.progress;
    if (data.totalSpecs !== undefined) result.total_specs = data.totalSpecs;
    if (data.completedSpecs !== undefined) result.completed_specs = data.completedSpecs;
    if (data.activeAgents !== undefined) result.active_agents = data.activeAgents;
    if (data.lastActivityAt !== undefined) result.last_activity_at = data.lastActivityAt;
    if (data.metadata !== undefined) result.metadata = data.metadata;

    return result;
  }

  /**
   * Fetch all projects with optional filtering and search
   */
  async getProjects(params?: {
    status?: ProjectStatus;
    priority?: ProjectPriority;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ProjectListResponse> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.status) queryParams.append('status', params.status);
      if (params?.priority) queryParams.append('priority', params.priority);
      if (params?.search) queryParams.append('search', params.search);
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.offset) queryParams.append('offset', params.offset.toString());

      const queryString = queryParams.toString();
      const url = `${this.baseUrl}/api/projects${queryString ? `?${queryString}` : ''}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        projects: data.projects.map(this.transformProject),
        total: data.total,
        limit: data.limit,
        offset: data.offset,
      };
    } catch (error) {
      console.error('Error fetching projects:', error);
      throw error;
    }
  }

  /**
   * Fetch a single project by ID
   */
  async getProject(projectId: string): Promise<ProjectDetail> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch project: ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformProjectDetail(data);
    } catch (error) {
      console.error('Error fetching project:', error);
      throw error;
    }
  }

  /**
   * Fetch portfolio summary statistics
   */
  async getSummary(): Promise<ProjectSummary> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/stats/summary`);
      if (!response.ok) {
        throw new Error(`Failed to fetch summary: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        totalProjects: data.total_projects,
        projectsByStatus: data.by_status,
        projectsByPriority: {} as Record<ProjectPriority, number>,
        totalActiveAgents: data.total_active_agents,
        avgProgress: data.average_progress,
        totalSpecs: data.total_specs,
        completedSpecs: data.completed_specs,
        overallCompletionRate: data.total_specs > 0 ? data.completed_specs / data.total_specs : 0,
        recentActiveProjects: 0,
      };
    } catch (error) {
      console.error('Error fetching summary:', error);
      throw error;
    }
  }

  /**
   * Create a new project
   */
  async createProject(projectData: {
    name: string;
    status?: ProjectStatus;
    priority?: ProjectPriority;
    description?: string;
    progress?: number;
    totalSpecs?: number;
    completedSpecs?: number;
    activeAgents?: number;
    metadata?: Record<string, unknown>;
  }): Promise<Project> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.transformCreateRequest(projectData)),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create project');
      }

      const data = await response.json();
      return this.transformProject(data);
    } catch (error) {
      console.error('Error creating project:', error);
      throw error;
    }
  }

  /**
   * Update an existing project
   */
  async updateProject(
    projectId: string,
    projectData: Partial<{
      status: ProjectStatus;
      priority: ProjectPriority;
      description: string;
      progress: number;
      totalSpecs: number;
      completedSpecs: number;
      activeAgents: number;
      lastActivityAt: string;
      metadata: Record<string, unknown>;
    }>
  ): Promise<Project> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.transformUpdateRequest(projectData)),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update project');
      }

      const data = await response.json();
      return this.transformProject(data);
    } catch (error) {
      console.error('Error updating project:', error);
      throw error;
    }
  }

  /**
   * Delete a project (soft delete)
   */
  async deleteProject(projectId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete project');
      }
    } catch (error) {
      console.error('Error deleting project:', error);
      throw error;
    }
  }

  /**
   * Sync project data from related sessions
   */
  async syncProject(projectId: string): Promise<Project> {
    try {
      const response = await fetch(`${this.baseUrl}/api/portfolio/projects/${projectId}/sync`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to sync project: ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformProject(data);
    } catch (error) {
      console.error('Error syncing project:', error);
      throw error;
    }
  }

  /**
   * Get control history for a project
   */
  async getProjectControls(projectId: string, params?: {
    limit?: number;
    offset?: number;
  }): Promise<{ controls: ProjectControlHistoryEntry[]; total: number; limit: number; offset: number }> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.offset) queryParams.append('offset', params.offset.toString());

      const queryString = queryParams.toString();
      const url = `${this.baseUrl}/api/projects/${projectId}/controls${queryString ? `?${queryString}` : ''}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch project controls: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        controls: data.controls.map(this.transformControlHistory),
        total: data.total,
        limit: data.limit,
        offset: data.offset,
      };
    } catch (error) {
      console.error('Error fetching project controls:', error);
      throw error;
    }
  }

  /**
   * Pause a project
   */
  async pauseProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/pause`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to pause project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error pausing project:', error);
      throw error;
    }
  }

  /**
   * Resume a paused project
   */
  async resumeProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/resume`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to resume project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error resuming project:', error);
      throw error;
    }
  }

  /**
   * Skip remaining specs in a project
   */
  async skipProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/skip`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to skip project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error skipping project:', error);
      throw error;
    }
  }

  /**
   * Stop all agents in a project
   */
  async stopProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/stop`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to stop project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error stopping project:', error);
      throw error;
    }
  }

  /**
   * Retry failed specs in a project
   */
  async retryProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/retry`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to retry project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error retrying project:', error);
      throw error;
    }
  }

  /**
   * Restart a project from the beginning
   */
  async restartProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/restart`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to restart project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error restarting project:', error);
      throw error;
    }
  }

  /**
   * Queue a project for processing
   */
  async queueProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/queue`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to queue project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error queueing project:', error);
      throw error;
    }
  }

  /**
   * Cancel a queued project
   */
  async cancelProject(projectId: string): Promise<ControlResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/${projectId}/cancel`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to cancel project');
      }

      return await response.json();
    } catch (error) {
      console.error('Error cancelling project:', error);
      throw error;
    }
  }

  /**
   * Bulk control multiple projects
   */
  async bulkControlProjects(projectIds: string[], action: ProjectControlAction): Promise<BulkOperationResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/projects/bulk/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_ids: projectIds,
          action: action,
        } as BulkOperationRequest),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to perform bulk operation');
      }

      return await response.json();
    } catch (error) {
      console.error('Error performing bulk operation:', error);
      throw error;
    }
  }

  /**
   * Bulk pause multiple projects
   */
  async bulkPauseProjects(projectIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkControlProjects(projectIds, 'pause');
  }

  /**
   * Bulk resume multiple projects
   */
  async bulkResumeProjects(projectIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkControlProjects(projectIds, 'resume');
  }

  /**
   * Bulk stop multiple projects
   */
  async bulkStopProjects(projectIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkControlProjects(projectIds, 'stop');
  }

  /**
   * Transform API response to frontend Project type
   */
  private transformProject(data: any): Project {
    return {
      id: data.id,
      name: data.name,
      status: data.status,
      priority: data.priority,
      description: data.description,
      progress: data.progress,
      totalSpecs: data.total_specs,
      completedSpecs: data.completed_specs,
      activeAgents: data.active_agents,
      lastActivityAt: data.last_activity_at,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
      metadata: data.metadata,
    };
  }

  /**
   * Transform API response to frontend ProjectDetail type
   */
  private transformProjectDetail(data: any): ProjectDetail {
    return {
      ...this.transformProject(data),
      stats: {
        totalSessions: 0,
        activeSessions: 0,
      },
      recentSessions: (data.recent_sessions || []).map((s: any) => ({
        id: s.id,
        agentType: s.agent_type,
        status: s.status,
        startedAt: s.started_at,
        endedAt: s.ended_at,
        createdAt: s.created_at,
      })),
      controlHistory: (data.control_history || []).map(this.transformControlHistory),
    };
  }

  /**
   * Transform API response to frontend ProjectControlHistoryEntry type
   */
  private transformControlHistory(data: any): ProjectControlHistoryEntry {
    return {
      id: data.id,
      action: data.action,
      status: data.status,
      initiatedBy: data.initiatedBy,
      agentsAffected: data.agentsAffected,
      errorMessage: data.errorMessage,
      createdAt: data.createdAt,
      metadata: data.metadata,
    };
  }
}

// Singleton instance
let portfolioServiceInstance: PortfolioService | null = null;

export const getPortfolioService = (): PortfolioService => {
  if (!portfolioServiceInstance) {
    portfolioServiceInstance = new PortfolioService();
  }
  return portfolioServiceInstance;
};

export default PortfolioService;
