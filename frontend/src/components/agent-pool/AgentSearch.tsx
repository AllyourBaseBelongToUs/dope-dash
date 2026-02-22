'use client';

import { useState, useMemo, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Check, AlertCircle, X, Loader2 } from 'lucide-react';
import { searchAgents, filterAgents } from '@/lib/fuzzySearch';
import type { AgentPoolAgent, PoolAgentStatus } from '@/types';

interface AgentSearchProps {
  /** All agents to search through */
  agents: AgentPoolAgent[];
  /** Callback when an agent is selected */
  onSelect: (agent: AgentPoolAgent) => void;
  /** Optional filter function to limit which agents are shown */
  filterFn?: (agent: AgentPoolAgent) => boolean;
  /** Placeholder text for the search input */
  placeholder?: string;
  /** Maximum number of results to show */
  maxResults?: number;
  /** Whether to show only available agents */
  availableOnly?: boolean;
  /** Loading state */
  isLoading?: boolean;
  /** Currently selected agent ID */
  selectedAgentId?: string | null;
  /** Error message to display */
  error?: string | null;
}

export function AgentSearch({
  agents,
  onSelect,
  filterFn,
  placeholder = 'Search agents...',
  maxResults = 10,
  availableOnly = false,
  isLoading = false,
  selectedAgentId = null,
  error = null,
}: AgentSearchProps) {
  const [query, setQuery] = useState('');

  // Apply filters
  const filteredAgents = useMemo(() => {
    let result = agents;

    // Apply availableOnly filter
    if (availableOnly) {
      result = filterAgents(result, { availableOnly: true });
    }

    // Apply custom filter function
    if (filterFn) {
      result = result.filter(filterFn);
    }

    return result;
  }, [agents, availableOnly, filterFn]);

  // Apply fuzzy search
  const searchResults = useMemo(() => {
    return searchAgents(filteredAgents, query, maxResults);
  }, [filteredAgents, query, maxResults]);

  // Clear search
  const handleClear = useCallback(() => {
    setQuery('');
  }, []);

  // Get status styling
  const getStatusStyle = (status: PoolAgentStatus) => {
    switch (status) {
      case 'available':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'busy':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'offline':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'maintenance':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'draining':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="space-y-3">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="pl-9 pr-9"
          disabled={isLoading}
        />
        {query && !isLoading && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-500">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Count */}
      {query && searchResults.length > 0 && (
        <div className="text-xs text-muted-foreground">
          {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} found
        </div>
      )}

      {/* Search Results */}
      <ScrollArea className="max-h-60">
        <div className="space-y-1">
          {searchResults.length === 0 && !isLoading && (
            <div className="text-center py-4 text-sm text-muted-foreground">
              {query ? 'No agents match your search' : 'No agents available'}
            </div>
          )}

          {searchResults.map((agent) => (
            <button
              key={agent.id}
              onClick={() => onSelect(agent)}
              className={`w-full flex items-center justify-between p-3 rounded-lg hover:bg-accent text-left transition-colors ${
                selectedAgentId === agent.agentId ? 'bg-accent ring-2 ring-primary' : ''
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{agent.agentId}</div>
                <div className="text-xs text-muted-foreground flex items-center gap-2">
                  <span>{agent.agentType}</span>
                  <span className="text-muted-foreground/50">|</span>
                  <span>
                    Load: {agent.currentLoad}/{agent.maxCapacity}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                {/* Capabilities badges */}
                {agent.capabilities.slice(0, 2).map((cap) => (
                  <Badge key={cap} variant="outline" className="text-xs hidden sm:inline-flex">
                    {cap}
                  </Badge>
                ))}
                {agent.capabilities.length > 2 && (
                  <Badge variant="outline" className="text-xs hidden sm:inline-flex">
                    +{agent.capabilities.length - 2}
                  </Badge>
                )}

                {/* Status badge */}
                <Badge
                  variant="outline"
                  className={`text-xs gap-1 ${getStatusStyle(agent.status)}`}
                >
                  {agent.status === 'available' && <Check className="h-3 w-3" />}
                  {agent.status === 'offline' && <AlertCircle className="h-3 w-3" />}
                  {agent.status}
                </Badge>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
