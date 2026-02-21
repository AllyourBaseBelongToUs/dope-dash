'use client';

import { useState, useEffect } from 'react';
import { useAgentPoolStore } from '@/store/agentPoolStore';
import { PoolMetrics } from '@/components/agent-pool/PoolMetrics';
import { PoolFilters } from '@/components/agent-pool/PoolFilters';
import { AgentCard } from '@/components/agent-pool/AgentCard';
import { RegisterAgentDialog } from '@/components/agent-pool/RegisterAgentDialog';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw, AlertCircle, Server } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function AgentPoolPage() {
  const {
    agents,
    metrics,
    healthReport,
    isLoading,
    isRefreshing,
    error,
    statusFilter,
    agentTypeFilter,
    searchQuery,
    total,
    registerDialogOpen,
    fetchAgents,
    fetchMetrics,
    fetchHealthReport,
    fetchScalingRecommendation,
    registerAgent,
    unregisterAgent,
    setAgentStatus,
    setRegisterDialogOpen,
    setStatusFilter,
    setAgentTypeFilter,
    setSearchQuery,
    refresh,
    clearError,
  } = useAgentPoolStore();

  const [selectedAgent, setSelectedAgent] = useState<ReturnType<typeof useAgentPoolStore.getState>['selectedAgent']>(null);

  // Load initial data
  useEffect(() => {
    fetchAgents();
    fetchMetrics();
    fetchHealthReport();
    fetchScalingRecommendation();
  }, []);

  // Refresh when filters change
  useEffect(() => {
    fetchAgents();
  }, [statusFilter, agentTypeFilter, searchQuery]);

  // Auto-refresh interval
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [statusFilter, agentTypeFilter]);

  const handleClearFilters = () => {
    setStatusFilter('all');
    setAgentTypeFilter('all');
    setSearchQuery('');
  };

  const handleRegisterAgent = async (data: any) => {
    await registerAgent(data);
  };

  const handleDeleteAgent = async (agent: any) => {
    if (confirm(`Are you sure you want to unregister agent "${agent.agentId}"?`)) {
      await unregisterAgent(agent.id);
    }
  };

  const handleStatusChange = async (agentId: string, status: any) => {
    await setAgentStatus(agentId, status);
  };

  const filteredAgents = agents.filter((agent) => {
    if (searchQuery && !agent.agentId.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <Server className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Agent Pool</h1>
                <p className="text-xs text-muted-foreground">Distributed Agent Management</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refresh()}
                disabled={isLoading || isRefreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                size="sm"
                onClick={() => setRegisterDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Register Agent
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Error Alert */}
        {error && (
          <Alert className="border-red-500 bg-red-500/10 text-red-600">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button variant="ghost" size="sm" onClick={clearError}>
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Metrics Dashboard */}
        <PoolMetrics metrics={metrics} healthReport={healthReport} />

        {/* Filters */}
        <PoolFilters
          statusFilter={statusFilter}
          agentTypeFilter={agentTypeFilter}
          searchQuery={searchQuery}
          onStatusChange={setStatusFilter}
          onAgentTypeChange={setAgentTypeFilter}
          onSearchChange={setSearchQuery}
          onClearFilters={handleClearFilters}
          totalResults={filteredAgents.length}
        />

        {/* Loading State */}
        {isLoading && agents.length === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-64 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && filteredAgents.length === 0 && (
          <div className="text-center py-12">
            <Server className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No agents found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {hasActiveFilters(statusFilter, agentTypeFilter, searchQuery)
                ? 'Try adjusting your filters or search query'
                : 'Get started by registering your first agent to the pool'}
            </p>
            {!hasActiveFilters(statusFilter, agentTypeFilter, searchQuery) && (
              <Button onClick={() => setRegisterDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Register Agent
              </Button>
            )}
          </div>
        )}

        {/* Agent Grid */}
        {!isLoading && filteredAgents.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onSelect={setSelectedAgent}
                onDelete={handleDeleteAgent}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        )}

        {/* Pagination Info */}
        {!isLoading && filteredAgents.length > 0 && (
          <div className="text-center text-sm text-muted-foreground">
            Showing {filteredAgents.length} of {total} agent{total !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Register Agent Dialog */}
      <RegisterAgentDialog
        open={registerDialogOpen}
        onOpenChange={setRegisterDialogOpen}
        onSubmit={handleRegisterAgent}
        isLoading={isLoading}
      />
    </main>
  );
}

function hasActiveFilters(
  statusFilter: any,
  agentTypeFilter: any,
  searchQuery: string
): boolean {
  return statusFilter !== 'all' || agentTypeFilter !== 'all' || searchQuery.length > 0;
}
