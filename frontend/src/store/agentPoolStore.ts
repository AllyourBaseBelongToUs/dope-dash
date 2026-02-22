import { create } from 'zustand';
import type {
  AgentPoolAgent,
  PoolMetrics,
  PoolHealthReport,
  ScalingRecommendation,
  ScalingPolicy,
  ScalingEvent,
  AgentAssignRequest,
  AgentAssignResponse,
  AgentPoolCreateRequest,
  AgentPoolUpdateRequest,
  PoolAgentStatus,
  AgentType,
} from '@/types';
import { getAgentPoolService } from '@/services/agentPoolService';

interface AgentPoolState {
  // State
  agents: AgentPoolAgent[];
  selectedAgent: AgentPoolAgent | null;
  metrics: PoolMetrics | null;
  healthReport: PoolHealthReport | null;
  scalingRecommendation: ScalingRecommendation | null;
  scalingPolicy: ScalingPolicy | null;
  scalingHistory: ScalingEvent[];
  isLoading: boolean;
  isRefreshing: boolean;
  isDetecting: boolean;
  error: string | null;

  // Filters
  statusFilter: PoolAgentStatus | 'all';
  agentTypeFilter: AgentType | 'all';
  searchQuery: string;

  // Pagination
  total: number;
  limit: number;
  offset: number;

  // Dialog states
  registerDialogOpen: boolean;
  editDialogOpen: boolean;
  assignDialogOpen: boolean;
  policyDialogOpen: boolean;

  // Actions
  setAgents: (agents: AgentPoolAgent[]) => void;
  setSelectedAgent: (agent: AgentPoolAgent | null) => void;
  setMetrics: (metrics: PoolMetrics) => void;
  setHealthReport: (report: PoolHealthReport) => void;
  setScalingRecommendation: (recommendation: ScalingRecommendation) => void;
  setScalingPolicy: (policy: ScalingPolicy) => void;
  setScalingHistory: (history: ScalingEvent[]) => void;
  setLoading: (loading: boolean) => void;
  setRefreshing: (refreshing: boolean) => void;
  setDetecting: (detecting: boolean) => void;
  setError: (error: string | null) => void;
  setStatusFilter: (status: PoolAgentStatus | 'all') => void;
  setAgentTypeFilter: (type: AgentType | 'all') => void;
  setSearchQuery: (query: string) => void;
  setOffset: (offset: number) => void;
  setRegisterDialogOpen: (open: boolean) => void;
  setEditDialogOpen: (open: boolean) => void;
  setAssignDialogOpen: (open: boolean) => void;
  setPolicyDialogOpen: (open: boolean) => void;

  // API Actions - Pool Management
  fetchAgents: () => Promise<void>;
  fetchAgent: (poolId: string) => Promise<void>;
  fetchAgentByAgentId: (agentId: string) => Promise<void>;
  registerAgent: (data: AgentPoolCreateRequest) => Promise<void>;
  updateAgent: (poolId: string, data: AgentPoolUpdateRequest) => Promise<void>;
  unregisterAgent: (poolId: string) => Promise<void>;
  detectAgents: (projectDir?: string) => Promise<{ detected: number; agents: any[] }>;

  // API Actions - Agent Control
  setAgentStatus: (agentId: string, status: PoolAgentStatus) => Promise<void>;
  updateHeartbeat: (agentId: string, metadata?: Record<string, unknown>) => Promise<void>;
  assignAgent: (request: AgentAssignRequest) => Promise<AgentAssignResponse>;
  releaseAgent: (agentId: string, completed?: boolean) => Promise<void>;

  // API Actions - Metrics & Health
  fetchMetrics: () => Promise<void>;
  fetchHealthReport: () => Promise<void>;
  fetchScalingRecommendation: () => Promise<void>;

  // API Actions - Auto-Scaling
  fetchScalingPolicy: () => Promise<void>;
  updateScalingPolicy: (policy: ScalingPolicy) => Promise<void>;
  fetchScalingHistory: () => Promise<void>;
  executeScaling: () => Promise<ScalingEvent>;
  startMonitoring: (intervalSeconds?: number) => Promise<void>;
  stopMonitoring: () => Promise<void>;

  // Utility Actions
  refresh: () => Promise<void>;
  clearError: () => void;
}

export const useAgentPoolStore = create<AgentPoolState>((set, get) => ({
  // Initial state
  agents: [],
  selectedAgent: null,
  metrics: null,
  healthReport: null,
  scalingRecommendation: null,
  scalingPolicy: {
    minAgents: 1,
    maxAgents: 10,
    scaleUpThreshold: 80,
    scaleDownThreshold: 20,
    scaleUpCooldownMinutes: 5,
    scaleDownCooldownMinutes: 10,
    staleAgentTimeoutMinutes: 5,
    enableAutoScaling: false,
  },
  scalingHistory: [],
  isLoading: false,
  isRefreshing: false,
  isDetecting: false,
  error: null,

  // Filters
  statusFilter: 'all',
  agentTypeFilter: 'all',
  searchQuery: '',

  // Pagination
  total: 0,
  limit: 100,
  offset: 0,

  // Dialog states
  registerDialogOpen: false,
  editDialogOpen: false,
  assignDialogOpen: false,
  policyDialogOpen: false,

  // Setters
  setAgents: (agents) => set({ agents }),
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setMetrics: (metrics) => set({ metrics }),
  setHealthReport: (report) => set({ healthReport: report }),
  setScalingRecommendation: (recommendation) => set({ scalingRecommendation: recommendation }),
  setScalingPolicy: (policy) => set({ scalingPolicy: policy }),
  setScalingHistory: (history) => set({ scalingHistory: history }),
  setLoading: (isLoading) => set({ isLoading }),
  setRefreshing: (isRefreshing) => set({ isRefreshing }),
  setDetecting: (isDetecting) => set({ isDetecting }),
  setError: (error) => set({ error }),
  setStatusFilter: (statusFilter) => set({ statusFilter, offset: 0 }),
  setAgentTypeFilter: (agentTypeFilter) => set({ agentTypeFilter, offset: 0 }),
  setSearchQuery: (searchQuery) => set({ searchQuery, offset: 0 }),
  setOffset: (offset) => set({ offset }),
  setRegisterDialogOpen: (registerDialogOpen) => set({ registerDialogOpen }),
  setEditDialogOpen: (editDialogOpen) => set({ editDialogOpen }),
  setAssignDialogOpen: (assignDialogOpen) => set({ assignDialogOpen }),
  setPolicyDialogOpen: (policyDialogOpen) => set({ policyDialogOpen }),

  // API Actions - Pool Management
  fetchAgents: async () => {
    const { statusFilter, agentTypeFilter, limit, offset } = get();
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const response = await service.listAgents({
        status: statusFilter === 'all' ? undefined : statusFilter,
        agentType: agentTypeFilter === 'all' ? undefined : agentTypeFilter,
        limit,
        offset,
      });

      set({
        agents: response.agents,
        total: response.total,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch agents',
        isLoading: false,
      });
    }
  },

  fetchAgent: async (poolId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const agent = await service.getAgent(poolId);

      if (agent) {
        set({ selectedAgent: agent, isLoading: false });
      } else {
        set({ error: 'Agent not found', isLoading: false });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch agent',
        isLoading: false,
      });
    }
  },

  fetchAgentByAgentId: async (agentId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const agent = await service.getAgentByAgentId(agentId);

      if (agent) {
        set({ selectedAgent: agent, isLoading: false });
      } else {
        set({ error: 'Agent not found', isLoading: false });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch agent',
        isLoading: false,
      });
    }
  },

  registerAgent: async (data: AgentPoolCreateRequest) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      await service.registerAgent(data);

      // Refresh the list
      await get().fetchAgents();
      set({ isLoading: false, registerDialogOpen: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to register agent',
        isLoading: false,
      });
      throw error;
    }
  },

  updateAgent: async (poolId: string, data: AgentPoolUpdateRequest) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const updated = await service.updateAgent(poolId, data);

      if (updated) {
        // Update in list
        set((state) => ({
          agents: state.agents.map((a) => (a.id === poolId ? updated : a)),
          selectedAgent: updated,
          isLoading: false,
          editDialogOpen: false,
        }));
      } else {
        set({ error: 'Agent not found', isLoading: false });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update agent',
        isLoading: false,
      });
      throw error;
    }
  },

  unregisterAgent: async (poolId: string) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      await service.unregisterAgent(poolId);

      // Remove from list
      set((state) => ({
        agents: state.agents.filter((a) => a.id !== poolId),
        selectedAgent: null,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to unregister agent',
        isLoading: false,
      });
      throw error;
    }
  },

  detectAgents: async (projectDir?: string) => {
    set({ isDetecting: true, error: null });

    try {
      const service = getAgentPoolService();
      const result = await service.detectAgents(projectDir);

      // Refresh the list after detection
      await get().fetchAgents();
      await get().fetchMetrics();

      set({ isDetecting: false });
      return { detected: result.detected, agents: result.agents };
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to detect agents',
        isDetecting: false,
      });
      throw error;
    }
  },

  // API Actions - Agent Control
  setAgentStatus: async (agentId: string, status: PoolAgentStatus) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const updated = await service.setAgentStatus(agentId, status);

      if (updated) {
        // Update in list
        set((state) => ({
          agents: state.agents.map((a) => (a.agentId === agentId ? updated : a)),
          selectedAgent: state.selectedAgent?.agentId === agentId ? updated : state.selectedAgent,
          isLoading: false,
        }));
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to set agent status',
        isLoading: false,
      });
      throw error;
    }
  },

  updateHeartbeat: async (agentId: string, metadata?: Record<string, unknown>) => {
    try {
      const service = getAgentPoolService();
      const updated = await service.updateHeartbeat({ agentId, metadata: metadata || {} });

      if (updated) {
        set((state) => ({
          agents: state.agents.map((a) => (a.agentId === agentId ? updated : a)),
          selectedAgent: state.selectedAgent?.agentId === agentId ? updated : state.selectedAgent,
        }));
      }
    } catch (error) {
      console.error('Failed to update heartbeat:', error);
    }
  },

  assignAgent: async (request: AgentAssignRequest) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const response = await service.assignAgent(request);

      set({ isLoading: false });
      return response;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to assign agent',
        isLoading: false,
      });
      throw error;
    }
  },

  releaseAgent: async (agentId: string, completed: boolean = true) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const updated = await service.releaseAgent(agentId, completed);

      if (updated) {
        set((state) => ({
          agents: state.agents.map((a) => (a.agentId === agentId ? updated : a)),
          selectedAgent: state.selectedAgent?.agentId === agentId ? updated : state.selectedAgent,
          isLoading: false,
        }));
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to release agent',
        isLoading: false,
      });
      throw error;
    }
  },

  // API Actions - Metrics & Health
  fetchMetrics: async () => {
    try {
      const service = getAgentPoolService();
      const metrics = await service.getPoolMetrics();
      set({ metrics, error: null });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch metrics';
      console.error('Failed to fetch metrics:', error);
      set({ error: errorMessage });
    }
  },

  fetchHealthReport: async () => {
    try {
      const service = getAgentPoolService();
      const report = await service.getHealthReport();
      set({ healthReport: report, error: null });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch health report';
      console.error('Failed to fetch health report:', error);
      set({ error: errorMessage });
    }
  },

  fetchScalingRecommendation: async () => {
    try {
      const service = getAgentPoolService();
      const recommendation = await service.getScalingRecommendation();
      set({ scalingRecommendation: recommendation, error: null });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch scaling recommendation';
      console.error('Failed to fetch scaling recommendation:', error);
      set({ error: errorMessage });
    }
  },

  // API Actions - Auto-Scaling
  fetchScalingPolicy: async () => {
    try {
      const service = getAgentPoolService();
      const policy = await service.getScalingPolicy();
      set({ scalingPolicy: policy, error: null });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch scaling policy';
      console.error('Failed to fetch scaling policy:', error);
      set({ error: errorMessage });
    }
  },

  updateScalingPolicy: async (policy: ScalingPolicy) => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const updated = await service.updateScalingPolicy(policy);
      set({ scalingPolicy: updated, isLoading: false, policyDialogOpen: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update scaling policy',
        isLoading: false,
      });
      throw error;
    }
  },

  fetchScalingHistory: async () => {
    try {
      const service = getAgentPoolService();
      const history = await service.getScalingHistory(50);
      set({ scalingHistory: history, error: null });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch scaling history';
      console.error('Failed to fetch scaling history:', error);
      set({ error: errorMessage });
    }
  },

  executeScaling: async () => {
    set({ isLoading: true, error: null });

    try {
      const service = getAgentPoolService();
      const event = await service.executeScaling();

      // Add to history and refresh
      set((state) => ({
        scalingHistory: [event, ...state.scalingHistory],
        isLoading: false,
      }));

      await get().fetchScalingRecommendation();
      return event;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to execute scaling',
        isLoading: false,
      });
      throw error;
    }
  },

  startMonitoring: async (intervalSeconds: number = 60) => {
    try {
      const service = getAgentPoolService();
      await service.startMonitoring(intervalSeconds);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to start monitoring',
      });
      throw error;
    }
  },

  stopMonitoring: async () => {
    try {
      const service = getAgentPoolService();
      await service.stopMonitoring();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to stop monitoring',
      });
      throw error;
    }
  },

  // Utility Actions
  refresh: async () => {
    set({ isRefreshing: true });
    try {
      await Promise.all([
        get().fetchAgents(),
        get().fetchMetrics(),
        get().fetchHealthReport(),
        get().fetchScalingRecommendation(),
      ]);
    } finally {
      set({ isRefreshing: false });
    }
  },

  clearError: () => set({ error: null }),
}));
