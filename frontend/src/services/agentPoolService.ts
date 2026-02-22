import type {
  AgentPoolAgent,
  AgentPoolListResponse,
  PoolMetrics,
  PoolHealthReport,
  ScalingRecommendation,
  ScalingPolicy,
  ScalingEvent,
  AgentAssignRequest,
  AgentAssignResponse,
  AgentHeartbeatRequest,
  AgentPoolCreateRequest,
  AgentPoolUpdateRequest,
  PoolAgentStatus,
  AgentType,
} from '@/types';

/**
 * Agent Pool Service
 * Handles all API calls for agent pool management, load balancing,
 * health monitoring, and auto-scaling.
 */
class AgentPoolService {
  private baseUrl: string = '';

  constructor() {
    if (typeof window !== 'undefined') {
      this.baseUrl = this.getApiBaseUrl();
    }
  }

  /**
   * Get CSRF token from meta tag or cookie
   */
  private getCsrfToken(): string | null {
    if (typeof document === 'undefined') return null;

    // Try meta tag first
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute('content');
    }

    // Try cookie
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrf_token' || name === 'XSRF-TOKEN') {
        return decodeURIComponent(value);
      }
    }

    return null;
  }

  /**
   * Get default headers for fetch requests
   */
  private getHeaders(includeCsrf: boolean = false): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (includeCsrf) {
      const csrfToken = this.getCsrfToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    return headers;
  }

  /**
   * Make a fetch request with proper credentials and CSRF protection
   */
  private async fetchWithCsrf(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const includeCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(
      (options.method || 'GET').toUpperCase()
    );

    return fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(includeCsrf),
        ...options.headers,
      },
      credentials: 'include', // Include cookies for session management
    });
  }

  /**
   * Get the API base URL from environment store or fallback
   */
  private getApiBaseUrl(): string {
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
   * Transform snake_case API response to camelCase frontend model
   */
  private transformAgent(data: any): AgentPoolAgent {
    return {
      id: data.id,
      agentId: data.agent_id,
      agentType: data.agent_type,
      status: data.status,
      currentProjectId: data.current_project_id,
      currentLoad: data.current_load,
      maxCapacity: data.max_capacity,
      capabilities: data.capabilities || [],
      metadata: data.metadata || {},
      pid: data.pid,
      workingDir: data.working_dir,
      command: data.command,
      tmuxSession: data.tmux_session,
      lastHeartbeat: data.last_heartbeat,
      totalAssigned: data.total_assigned,
      totalCompleted: data.total_completed,
      totalFailed: data.total_failed,
      averageTaskDurationMs: data.average_task_duration_ms,
      affinityTag: data.affinity_tag,
      priority: data.priority,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
      deletedAt: data.deleted_at,
      utilizationPercent: data.utilization_percent || 0,
      completionRate: data.completion_rate || 0,
      isAvailable: data.is_available ?? true,
    };
  }

  /**
   * Transform camelCase frontend request to snake_case API format
   */
  private transformCreateRequest(data: AgentPoolCreateRequest): any {
    return {
      agent_id: data.agentId,
      agent_type: data.agentType,
      status: data.status,
      current_project_id: data.currentProjectId,
      current_load: data.currentLoad,
      max_capacity: data.maxCapacity,
      capabilities: data.capabilities,
      metadata: data.metadata,
      pid: data.pid,
      working_dir: data.workingDir,
      command: data.command,
      tmux_session: data.tmuxSession,
      last_heartbeat: data.lastHeartbeat,
      total_assigned: data.totalAssigned,
      total_completed: data.totalCompleted,
      total_failed: data.totalFailed,
      average_task_duration_ms: data.averageTaskDurationMs,
      affinity_tag: data.affinityTag,
      priority: data.priority,
    };
  }

  /**
   * Transform camelCase frontend update request to snake_case API format
   */
  private transformUpdateRequest(data: AgentPoolUpdateRequest): any {
    const result: any = {};
    if (data.status !== undefined) result.status = data.status;
    if (data.currentProjectId !== undefined) result.current_project_id = data.currentProjectId;
    if (data.currentLoad !== undefined) result.current_load = data.currentLoad;
    if (data.maxCapacity !== undefined) result.max_capacity = data.maxCapacity;
    if (data.capabilities !== undefined) result.capabilities = data.capabilities;
    if (data.metadata !== undefined) result.metadata = data.metadata;
    if (data.pid !== undefined) result.pid = data.pid;
    if (data.workingDir !== undefined) result.working_dir = data.workingDir;
    if (data.command !== undefined) result.command = data.command;
    if (data.tmuxSession !== undefined) result.tmux_session = data.tmuxSession;
    if (data.lastHeartbeat !== undefined) result.last_heartbeat = data.lastHeartbeat;
    if (data.totalAssigned !== undefined) result.total_assigned = data.totalAssigned;
    if (data.totalCompleted !== undefined) result.total_completed = data.totalCompleted;
    if (data.totalFailed !== undefined) result.total_failed = data.totalFailed;
    if (data.averageTaskDurationMs !== undefined) result.average_task_duration_ms = data.averageTaskDurationMs;
    if (data.affinityTag !== undefined) result.affinity_tag = data.affinityTag;
    if (data.priority !== undefined) result.priority = data.priority;
    return result;
  }

  // ============================================================================
  // Pool Management Methods
  // ============================================================================

  /**
   * List all agents in the pool with optional filtering
   */
  async listAgents(params?: {
    status?: PoolAgentStatus;
    agentType?: AgentType;
    limit?: number;
    offset?: number;
  }): Promise<AgentPoolListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.agentType) queryParams.append('agent_type', params.agentType);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());

    const url = `${this.baseUrl}/api/agent-pool${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch agents: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      agents: data.agents.map((a: any) => this.transformAgent(a)),
      total: data.total,
      limit: data.limit,
      offset: data.offset,
    };
  }

  /**
   * Register a new agent in the pool
   */
  async registerAgent(data: AgentPoolCreateRequest): Promise<AgentPoolAgent> {
    const url = `${this.baseUrl}/api/agent-pool`;
    const response = await this.fetchWithCsrf(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.transformCreateRequest(data)),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Failed to register agent');
    }

    const agentData = await response.json();
    return this.transformAgent(agentData);
  }

  /**
   * Get an agent by pool ID
   */
  async getAgent(poolId: string): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/${poolId}`;
    const response = await this.fetchWithCsrf(url);

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to fetch agent: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformAgent(data);
  }

  /**
   * Get an agent by external agent_id
   */
  async getAgentByAgentId(agentId: string): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/agent-id/${agentId}`;
    const response = await this.fetchWithCsrf(url);

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to fetch agent: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformAgent(data);
  }

  /**
   * Update an agent
   */
  async updateAgent(poolId: string, data: AgentPoolUpdateRequest): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/${poolId}`;
    const response = await this.fetchWithCsrf(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.transformUpdateRequest(data)),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to update agent: ${response.statusText}`);
    }

    const agentData = await response.json();
    return this.transformAgent(agentData);
  }

  /**
   * Unregister an agent (soft delete)
   */
  async unregisterAgent(poolId: string): Promise<boolean> {
    const url = `${this.baseUrl}/api/agent-pool/${poolId}`;
    const response = await this.fetchWithCsrf(url, { method: 'DELETE' });

    if (response.status === 404) return false;
    if (!response.ok) {
      throw new Error(`Failed to unregister agent: ${response.statusText}`);
    }

    return true;
  }

  // ============================================================================
  // Agent Control Methods
  // ============================================================================

  /**
   * Set an agent's status by external agent_id
   */
  async setAgentStatus(agentId: string, status: PoolAgentStatus): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/${agentId}/status?status=${status}`;
    const response = await this.fetchWithCsrf(url, { method: 'POST' });

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to set agent status: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformAgent(data);
  }

  /**
   * Update an agent's heartbeat
   */
  async updateHeartbeat(data: AgentHeartbeatRequest): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/heartbeat`;
    const response = await this.fetchWithCsrf(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: data.agentId,
        current_load: data.currentLoad,
        current_project_id: data.currentProjectId,
        metadata: data.metadata,
      }),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to update heartbeat: ${response.statusText}`);
    }

    const agentData = await response.json();
    return this.transformAgent(agentData);
  }

  /**
   * Assign an agent to a project
   */
  async assignAgent(request: AgentAssignRequest): Promise<AgentAssignResponse> {
    const url = `${this.baseUrl}/api/agent-pool/assign`;
    const response = await this.fetchWithCsrf(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: request.projectId,
        agent_type: request.agentType,
        capabilities: request.capabilities,
        affinity_tag: request.affinityTag,
        preferred_agent_id: request.preferredAgentId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to assign agent: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: data.success,
      agent: data.agent ? this.transformAgent(data.agent) : null,
      message: data.message,
    };
  }

  /**
   * Release an agent from its current assignment
   */
  async releaseAgent(agentId: string, completed: boolean = true): Promise<AgentPoolAgent | null> {
    const url = `${this.baseUrl}/api/agent-pool/${agentId}/release?completed=${completed}`;
    const response = await this.fetchWithCsrf(url, { method: 'POST' });

    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Failed to release agent: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformAgent(data);
  }

  // ============================================================================
  // Metrics Methods
  // ============================================================================

  /**
   * Get aggregate metrics for the agent pool
   */
  async getPoolMetrics(): Promise<PoolMetrics> {
    const url = `${this.baseUrl}/api/agent-pool/metrics/summary`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch pool metrics: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Get comprehensive health report for the agent pool
   */
  async getHealthReport(): Promise<PoolHealthReport> {
    const url = `${this.baseUrl}/api/agent-pool/metrics/health`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch health report: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      healthy: data.healthy,
      metrics: data.metrics,
      issues: data.issues || [],
      recommendations: data.recommendations || [],
      staleAgents: (data.stale_agents || []).map((a: any) => this.transformAgent(a)),
      overloadedAgents: (data.overloaded_agents || []).map((a: any) => this.transformAgent(a)),
    };
  }

  // ============================================================================
  // Agent Detection Methods
  // ============================================================================

  /**
   * Trigger manual agent detection scan
   */
  async detectAgents(projectDir?: string): Promise<{ detected: number; agents: any[]; sync: any }> {
    const params = projectDir ? `?project_dir=${encodeURIComponent(projectDir)}` : '';
    const url = `${this.baseUrl}/api/agent-pool/detect${params}`;
    const response = await this.fetchWithCsrf(url, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to trigger detection: ${response.statusText}`);
    }

    return await response.json();
  }

  // ============================================================================
  // Auto-Scaling Methods
  // ============================================================================

  /**
   * Get a scaling recommendation based on current pool metrics
   */
  async getScalingRecommendation(): Promise<ScalingRecommendation> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/recommendation`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch scaling recommendation: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Execute a scaling action based on current recommendation
   */
  async executeScaling(): Promise<ScalingEvent> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/execute`;
    const response = await this.fetchWithCsrf(url, { method: 'POST' });

    if (!response.ok) {
      throw new Error(`Failed to execute scaling: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      id: data.id,
      action: data.action,
      previousCount: data.previous_count,
      newCount: data.new_count,
      reason: data.reason,
      metadata: data.metadata,
      createdAt: data.created_at,
    };
  }

  /**
   * Get history of scaling events
   */
  async getScalingHistory(limit: number = 50): Promise<ScalingEvent[]> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/history?limit=${limit}`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch scaling history: ${response.statusText}`);
    }

    const data = await response.json();
    return data.events.map((e: any) => ({
      id: e.id,
      action: e.action,
      previousCount: e.previous_count,
      newCount: e.new_count,
      reason: e.reason,
      metadata: e.metadata,
      createdAt: e.created_at,
    }));
  }

  /**
   * Get the current auto-scaling policy configuration
   */
  async getScalingPolicy(): Promise<ScalingPolicy> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/policy`;
    const response = await this.fetchWithCsrf(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch scaling policy: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      minAgents: data.min_agents,
      maxAgents: data.max_agents,
      scaleUpThreshold: data.scale_up_threshold,
      scaleDownThreshold: data.scale_down_threshold,
      scaleUpCooldownMinutes: data.scale_up_cooldown_minutes,
      scaleDownCooldownMinutes: data.scale_down_cooldown_minutes,
      staleAgentTimeoutMinutes: data.stale_agent_timeout_minutes,
      enableAutoScaling: data.enable_auto_scaling,
    };
  }

  /**
   * Update the auto-scaling policy configuration
   */
  async updateScalingPolicy(policy: ScalingPolicy): Promise<ScalingPolicy> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/policy`;
    const response = await this.fetchWithCsrf(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        min_agents: policy.minAgents,
        max_agents: policy.maxAgents,
        scale_up_threshold: policy.scaleUpThreshold,
        scale_down_threshold: policy.scaleDownThreshold,
        scale_up_cooldown_minutes: policy.scaleUpCooldownMinutes,
        scale_down_cooldown_minutes: policy.scaleDownCooldownMinutes,
        stale_agent_timeout_minutes: policy.staleAgentTimeoutMinutes,
        enable_auto_scaling: policy.enableAutoScaling,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update scaling policy: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      minAgents: data.min_agents,
      maxAgents: data.max_agents,
      scaleUpThreshold: data.scale_up_threshold,
      scaleDownThreshold: data.scale_down_threshold,
      scaleUpCooldownMinutes: data.scale_up_cooldown_minutes,
      scaleDownCooldownMinutes: data.scale_down_cooldown_minutes,
      staleAgentTimeoutMinutes: data.stale_agent_timeout_minutes,
      enableAutoScaling: data.enable_auto_scaling,
    };
  }

  /**
   * Start auto-scaling monitoring
   */
  async startMonitoring(intervalSeconds: number = 60): Promise<{ status: string; message: string }> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/start?interval_seconds=${intervalSeconds}`;
    const response = await this.fetchWithCsrf(url, { method: 'POST' });

    if (!response.ok) {
      throw new Error(`Failed to start monitoring: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Stop auto-scaling monitoring
   */
  async stopMonitoring(): Promise<{ status: string; message: string }> {
    const url = `${this.baseUrl}/api/agent-pool/scaling/stop`;
    const response = await this.fetchWithCsrf(url, { method: 'POST' });

    if (!response.ok) {
      throw new Error(`Failed to stop monitoring: ${response.statusText}`);
    }

    return await response.json();
  }
}

// Singleton instance
let agentPoolServiceInstance: AgentPoolService | null = null;

export const getAgentPoolService = (): AgentPoolService => {
  if (!agentPoolServiceInstance) {
    agentPoolServiceInstance = new AgentPoolService();
  }
  return agentPoolServiceInstance;
};
