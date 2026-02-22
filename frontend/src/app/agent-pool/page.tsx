'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAgentPoolStore } from '@/store/agentPoolStore';
import { AppShell } from '@/components/AppShell';
import { PoolMetrics } from '@/components/agent-pool/PoolMetrics';
import { PoolFilters } from '@/components/agent-pool/PoolFilters';
import { AgentCard } from '@/components/agent-pool/AgentCard';
import { RegisterAgentDialog } from '@/components/agent-pool/RegisterAgentDialog';
import { AgentSearch } from '@/components/agent-pool/AgentSearch';
import { AssignmentDnDContext } from '@/components/dnd';
import { DroppableZone, EmptyDropZone } from '@/components/dnd/DroppableZone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, RefreshCw, AlertCircle, Server, Search, FolderPlus, ArrowRightLeft, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from '@/components/ui/use-toast';
import type { AgentPoolAgent, PoolAgentStatus, AgentPoolCreateRequest } from '@/types';

export default function AgentPoolPage() {
  const {
    agents,
    metrics,
    healthReport,
    isLoading,
    isRefreshing,
    isDetecting,
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
    detectAgents,
    assignAgent,
    setRegisterDialogOpen,
    setStatusFilter,
    setAgentTypeFilter,
    setSearchQuery,
    refresh,
    clearError,
  } = useAgentPoolStore();

  const [selectedAgent, setSelectedAgent] = useState<AgentPoolAgent | null>(null);
  const [showSearchPanel, setShowSearchPanel] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<AgentPoolAgent | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [statusChangeLoading, setStatusChangeLoading] = useState<string | null>(null);

  // Track mounted state for async operations
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Handle drag-and-drop assignment
  const handleAssign = useCallback(async (agentId: string, projectId: string) => {
    setIsAssigning(true);
    try {
      const response = await assignAgent({
        projectId,
        preferredAgentId: agentId,
        capabilities: [],
      });

      // Check if component is still mounted
      if (!isMountedRef.current) return;

      if (response.success) {
        toast({
          title: 'Agent assigned',
          description: `Agent ${agentId} assigned to project successfully`,
        });
        // Refresh to show updated load
        await refresh();
      } else {
        toast({
          variant: 'destructive',
          title: 'Assignment failed',
          description: response.message || 'Failed to assign agent',
        });
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      toast({
        variant: 'destructive',
        title: 'Assignment failed',
        description: err instanceof Error ? err.message : 'Failed to assign agent',
      });
    } finally {
      if (isMountedRef.current) {
        setIsAssigning(false);
      }
    }
  }, [assignAgent, refresh]);

  // Load initial data
  useEffect(() => {
    fetchAgents();
    fetchMetrics();
    fetchHealthReport();
    fetchScalingRecommendation();
  }, [fetchAgents, fetchMetrics, fetchHealthReport, fetchScalingRecommendation]);

  // Refresh when filters change
  useEffect(() => {
    fetchAgents();
  }, [statusFilter, agentTypeFilter, searchQuery, fetchAgents]);

  // Auto-refresh interval
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [statusFilter, agentTypeFilter, refresh]);

  const handleClearFilters = () => {
    setStatusFilter('all');
    setAgentTypeFilter('all');
    setSearchQuery('');
  };

  const handleRegisterAgent = async (data: AgentPoolCreateRequest) => {
    try {
      await registerAgent(data);
      toast({
        title: 'Agent registered',
        description: `Agent ${data.agentId} has been registered successfully`,
      });
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Registration failed',
        description: err instanceof Error ? err.message : 'Failed to register agent',
      });
    }
  };

  const handleDeleteAgent = async (agent: AgentPoolAgent) => {
    setAgentToDelete(agent);
  };

  const confirmDeleteAgent = async () => {
    if (!agentToDelete) return;

    setIsDeleting(true);
    try {
      await unregisterAgent(agentToDelete.id);
      if (isMountedRef.current) {
        toast({
          title: 'Agent unregistered',
          description: `Agent ${agentToDelete.agentId} has been removed from the pool`,
        });
        setAgentToDelete(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        toast({
          variant: 'destructive',
          title: 'Unregister failed',
          description: err instanceof Error ? err.message : 'Failed to unregister agent',
        });
      }
    } finally {
      if (isMountedRef.current) {
        setIsDeleting(false);
      }
    }
  };

  const handleStatusChange = async (agentId: string, status: PoolAgentStatus) => {
    setStatusChangeLoading(agentId);
    try {
      await setAgentStatus(agentId, status);
      if (isMountedRef.current) {
        toast({
          title: 'Status updated',
          description: `Agent ${agentId} status changed to ${status}`,
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        toast({
          variant: 'destructive',
          title: 'Status change failed',
          description: err instanceof Error ? err.message : 'Failed to change agent status',
        });
      }
    } finally {
      if (isMountedRef.current) {
        setStatusChangeLoading(null);
      }
    }
  };

  const handleDetectAgents = async () => {
    try {
      const result = await detectAgents();
      if (isMountedRef.current) {
        toast({
          title: 'Scan complete',
          description: `Found ${result.detected} agent${result.detected !== 1 ? 's' : ''}`,
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        toast({
          variant: 'destructive',
          title: 'Scan failed',
          description: err instanceof Error ? err.message : 'Failed to scan for agents',
        });
      }
    }
  };

  const filteredAgents = agents.filter((agent) => {
    if (searchQuery && !agent.agentId.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const pageActions = (
    <>
      <Button
        variant={showSearchPanel ? 'default' : 'outline'}
        size="sm"
        onClick={() => setShowSearchPanel(!showSearchPanel)}
      >
        <Search className="h-4 w-4 mr-2" />
        Search
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleDetectAgents}
        disabled={isLoading || isRefreshing || isDetecting}
      >
        <Search className={`h-4 w-4 mr-2 ${isDetecting ? 'animate-pulse' : ''}`} />
        {isDetecting ? 'Scanning...' : 'Scan for Agents'}
      </Button>
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
    </>
  );

  return (
    <AssignmentDnDContext onAssign={handleAssign}>
      <AppShell
        title="Agent Pool"
        subtitle="Distributed Agent Management"
        icon={<Server className="h-5 w-5 text-primary" />}
        actions={pageActions}
        agentCount={agents.length}
      >
        {/* Error Alert */}
        {error && (
          <Alert className="border-red-500 bg-red-500/10 text-red-600 mb-6">
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

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Agent Grid */}
          <div className="lg:col-span-3">
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
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredAgents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    onSelect={setSelectedAgent}
                    onDelete={handleDeleteAgent}
                    onStatusChange={handleStatusChange}
                    draggable={true}
                  />
                ))}
              </div>
            )}

            {/* Pagination Info */}
            {!isLoading && filteredAgents.length > 0 && (
              <div className="text-center text-sm text-muted-foreground mt-4">
                Showing {filteredAgents.length} of {total} agent{total !== 1 ? 's' : ''}
              </div>
            )}
          </div>

          {/* Side Panel - Search & Drop Zone */}
          <div className="lg:col-span-1 space-y-4">
            {/* Search Panel */}
            {showSearchPanel && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    Quick Search
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <AgentSearch
                    agents={agents}
                    onSelect={(agent) => {
                      setSelectedAgent(agent);
                      setShowSearchPanel(false);
                    }}
                    availableOnly={false}
                    placeholder="Find an agent..."
                    selectedAgentId={selectedAgent?.agentId}
                  />
                </CardContent>
              </Card>
            )}

            {/* Drop Zone for Projects */}
            <Card className="border-dashed">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FolderPlus className="h-4 w-4" />
                  Assign Project
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DroppableZone
                  id="unassigned-projects-zone"
                  type="project"
                  data={{ zoneType: 'unassigned' }}
                  className="min-h-24"
                >
                  <EmptyDropZone
                    idleText="Drag a project here to assign it to this agent pool"
                    hoverText="Release to view available agents"
                    icon={<ArrowRightLeft className="h-6 w-6 text-muted-foreground" />}
                  />
                </DroppableZone>
                <p className="text-xs text-muted-foreground mt-2 text-center">
                  Projects from the Portfolio page can be dropped here
                </p>
              </CardContent>
            </Card>

            {/* Selected Agent Info */}
            {selectedAgent && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Selected Agent</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-sm">
                    <span className="font-medium">{selectedAgent.agentId}</span>
                    <span className="text-muted-foreground ml-2">({selectedAgent.agentType})</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Status: {selectedAgent.status} | Load: {selectedAgent.currentLoad}/{selectedAgent.maxCapacity}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full mt-2"
                    onClick={() => setSelectedAgent(null)}
                  >
                    Clear Selection
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Register Agent Dialog */}
        <RegisterAgentDialog
          open={registerDialogOpen}
          onOpenChange={setRegisterDialogOpen}
          onSubmit={handleRegisterAgent}
          isLoading={isLoading}
        />

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={!!agentToDelete} onOpenChange={(open) => !open && setAgentToDelete(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Unregister Agent</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to unregister agent <strong>{agentToDelete?.agentId}</strong>?
                This will remove the agent from the pool and it will no longer be available for assignment.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={confirmDeleteAgent}
                disabled={isDeleting}
                className="bg-red-600 hover:bg-red-700"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Unregistering...
                  </>
                ) : (
                  'Unregister'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </AppShell>
    </AssignmentDnDContext>
  );
}

function hasActiveFilters(
  statusFilter: string,
  agentTypeFilter: string,
  searchQuery: string
): boolean {
  return statusFilter !== 'all' || agentTypeFilter !== 'all' || searchQuery.length > 0;
}
