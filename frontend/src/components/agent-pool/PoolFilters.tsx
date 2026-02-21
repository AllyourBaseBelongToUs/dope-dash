'use client';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, X } from 'lucide-react';
import type { PoolAgentStatus, AgentType } from '@/types';

interface PoolFiltersProps {
  statusFilter: PoolAgentStatus | 'all';
  agentTypeFilter: AgentType | 'all';
  searchQuery: string;
  onStatusChange: (status: PoolAgentStatus | 'all') => void;
  onAgentTypeChange: (type: AgentType | 'all') => void;
  onSearchChange: (query: string) => void;
  onClearFilters: () => void;
  totalResults: number;
}

export function PoolFilters({
  statusFilter,
  agentTypeFilter,
  searchQuery,
  onStatusChange,
  onAgentTypeChange,
  onSearchChange,
  onClearFilters,
  totalResults,
}: PoolFiltersProps) {
  const hasActiveFilters = statusFilter !== 'all' || agentTypeFilter !== 'all' || searchQuery.length > 0;

  const agentTypes: (AgentType | 'all')[] = [
    'all',
    'ralph',
    'claude',
    'cursor',
    'terminal',
    'crawler',
    'analyzer',
    'reporter',
    'tester',
    'custom',
  ];

  const statuses: (PoolAgentStatus | 'all')[] = [
    'all',
    'available',
    'busy',
    'offline',
    'maintenance',
    'draining',
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by agent ID..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
          {searchQuery && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
              onClick={() => onSearchChange('')}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Status Filter */}
        <Select value={statusFilter} onValueChange={onStatusChange}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {statuses.map((status) => (
              <SelectItem key={status} value={status}>
                {status === 'all' ? 'All Statuses' : status.charAt(0).toUpperCase() + status.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Agent Type Filter */}
        <Select value={agentTypeFilter} onValueChange={onAgentTypeChange}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            {agentTypes.map((type) => (
              <SelectItem key={type} value={type}>
                {type === 'all' ? 'All Types' : type.charAt(0).toUpperCase() + type.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button variant="outline" onClick={onClearFilters}>
            <X className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      {/* Active Filters & Results Count */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {hasActiveFilters ? (
            <>
              <span className="text-sm text-muted-foreground">Active filters:</span>
              {statusFilter !== 'all' && (
                <Badge variant="secondary">
                  Status: {statusFilter}
                </Badge>
              )}
              {agentTypeFilter !== 'all' && (
                <Badge variant="secondary">
                  Type: {agentTypeFilter}
                </Badge>
              )}
              {searchQuery && (
                <Badge variant="secondary">
                  Search: "{searchQuery}"
                </Badge>
              )}
            </>
          ) : (
            <span className="text-sm text-muted-foreground">Showing all agents</span>
          )}
        </div>
        <div className="text-sm text-muted-foreground">
          {totalResults} agent{totalResults !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}
