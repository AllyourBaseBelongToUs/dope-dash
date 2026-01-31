import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, X, Filter } from 'lucide-react';
import type { ProjectStatus, ProjectPriority } from '@/types';

interface ProjectFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: ProjectStatus | 'all';
  onStatusChange: (status: ProjectStatus | 'all') => void;
  priorityFilter: ProjectPriority | 'all';
  onPriorityChange: (priority: ProjectPriority | 'all') => void;
  onReset: () => void;
  resultCount?: number;
}

const STATUS_OPTIONS: Array<{ value: ProjectStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All Statuses' },
  { value: 'idle', label: 'Idle' },
  { value: 'running', label: 'Running' },
  { value: 'paused', label: 'Paused' },
  { value: 'error', label: 'Error' },
  { value: 'completed', label: 'Completed' },
];

const PRIORITY_OPTIONS: Array<{ value: ProjectPriority | 'all'; label: string }> = [
  { value: 'all', label: 'All Priorities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

export function ProjectFilters({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  priorityFilter,
  onPriorityChange,
  onReset,
  resultCount = 0,
}: ProjectFiltersProps) {
  const hasActiveFilters =
    searchQuery !== '' || statusFilter !== 'all' || priorityFilter !== 'all';

  return (
    <div className="space-y-4">
      {/* Search and Filters Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <h3 className="font-medium">Filters</h3>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="h-7 text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Reset
            </Button>
          )}
        </div>
        <div className="text-sm text-muted-foreground">
          {resultCount} project{resultCount !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Filter Dropdowns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Select
          value={statusFilter}
          onValueChange={(value) => onStatusChange(value as ProjectStatus | 'all')}
        >
          <SelectTrigger>
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={priorityFilter}
          onValueChange={(value) => onPriorityChange(value as ProjectPriority | 'all')}
        >
          <SelectTrigger>
            <SelectValue placeholder="Filter by priority" />
          </SelectTrigger>
          <SelectContent>
            {PRIORITY_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Active Filter Tags */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2">
          {searchQuery && (
            <div className="inline-flex items-center gap-1 px-2 py-1 bg-secondary rounded-md text-xs">
              <span>Search: "{searchQuery}"</span>
              <button
                onClick={() => onSearchChange('')}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          {statusFilter !== 'all' && (
            <div className="inline-flex items-center gap-1 px-2 py-1 bg-secondary rounded-md text-xs">
              <span>Status: {statusFilter}</span>
              <button
                onClick={() => onStatusChange('all')}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          {priorityFilter !== 'all' && (
            <div className="inline-flex items-center gap-1 px-2 py-1 bg-secondary rounded-md text-xs">
              <span>Priority: {priorityFilter}</span>
              <button
                onClick={() => onPriorityChange('all')}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
