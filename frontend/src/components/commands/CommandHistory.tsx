'use client';

import * as React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Star,
  StarOff,
  RotateCcw,
  Download,
  Search,
  Filter,
  Loader2,
  Terminal,
  Clock,
  CheckCircle,
  XCircle,
  Loader,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  CommandHistoryEntry,
  CommandStatus,
} from '@/types';
import { getCommandService } from '@/services/commandService';

interface CommandHistoryProps {
  projectId: string;
  onCommandReplayed?: (command: string) => void;
}

const STATUS_CONFIG: Record<
  CommandStatus,
  { icon: typeof CheckCircle; label: string; className: string }
> = {
  pending: { icon: Loader, label: 'Pending', className: 'bg-yellow-500/10 text-yellow-500' },
  sent: { icon: Loader, label: 'Sent', className: 'bg-blue-500/10 text-blue-500' },
  acknowledged: {
    icon: Terminal,
    label: 'Acknowledged',
    className: 'bg-purple-500/10 text-purple-500',
  },
  completed: {
    icon: CheckCircle,
    label: 'Completed',
    className: 'bg-green-500/10 text-green-500',
  },
  failed: { icon: XCircle, label: 'Failed', className: 'bg-red-500/10 text-red-500' },
  timeout: { icon: Clock, label: 'Timeout', className: 'bg-orange-500/10 text-orange-500' },
};

export function CommandHistory({ projectId, onCommandReplayed }: CommandHistoryProps) {
  const [commands, setCommands] = React.useState<CommandHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isReplaying, setIsReplaying] = React.useState<string | null>(null);
  const [isTogglingFavorite, setIsTogglingFavorite] = React.useState<string | null>(null);
  const [isExporting, setIsExporting] = React.useState(false);
  const [filter, setFilter] = React.useState<CommandStatus | 'all'>('all');
  const [search, setSearch] = React.useState('');
  const [showFavoritesOnly, setShowFavoritesOnly] = React.useState(false);
  const [page, setPage] = React.useState(0);
  const [total, setTotal] = React.useState(0);

  const commandService = getCommandService();
  const limit = 20;

  React.useEffect(() => {
    loadCommands();
  }, [projectId, filter, showFavoritesOnly, page]);

  const loadCommands = async () => {
    setIsLoading(true);
    try {
      const response = await commandService.getProjectCommandHistory(projectId, {
        status: filter === 'all' ? undefined : filter,
        isFavorite: showFavoritesOnly || undefined,
        limit,
        offset: page * limit,
      });
      setCommands(response.commands);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load command history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleFavorite = async (commandId: string, currentFavorite: boolean) => {
    setIsTogglingFavorite(commandId);
    try {
      await commandService.toggleCommandFavorite(commandId, !currentFavorite);
      await loadCommands();
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    } finally {
      setIsTogglingFavorite(null);
    }
  };

  const handleReplay = async (commandId: string) => {
    setIsReplaying(commandId);
    try {
      const command = await commandService.replayCommand({ commandId });
      onCommandReplayed?.(command.command);
    } catch (error) {
      console.error('Failed to replay command:', error);
    } finally {
      setIsReplaying(null);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await commandService.exportCommandHistory(projectId, {
        status: filter === 'all' ? undefined : filter,
        isFavorite: showFavoritesOnly || undefined,
      });
    } catch (error) {
      console.error('Failed to export command history:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const filteredCommands = React.useMemo(() => {
    if (!search) return commands;
    const searchLower = search.toLowerCase();
    return commands.filter(
      (c) =>
        c.command.toLowerCase().includes(searchLower) ||
        c.result?.toLowerCase().includes(searchLower) ||
        c.errorMessage?.toLowerCase().includes(searchLower)
    );
  }, [commands, search]);

  const StatusIcon = ({ status }: { status: CommandStatus }) => {
    const config = STATUS_CONFIG[status];
    const Icon = config.icon;
    return (
      <div className="flex items-center gap-1.5">
        <Icon className="h-3 w-3" />
        <span className="text-xs">{config.label}</span>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Command History</h3>
          <p className="text-muted-foreground text-sm">
            {total} command{total !== 1 ? 's' : ''} recorded
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          >
            <Star
              className={cn(
                'mr-2 h-4 w-4',
                showFavoritesOnly ? 'fill-yellow-400 text-yellow-400' : ''
              )}
            />
            {showFavoritesOnly ? 'All Commands' : 'Favorites Only'}
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search commands..."
            className="pl-9"
          />
        </div>
        <div className="flex gap-1">
          {(['all', 'completed', 'failed', 'pending'] as const).map((status) => (
            <Button
              key={status}
              variant={filter === status ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setFilter(status);
                setPage(0);
              }}
            >
              {status === 'all' ? 'All' : status}
            </Button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]"></TableHead>
              <TableHead>Command</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="hidden md:table-cell">Result</TableHead>
              <TableHead className="hidden lg:table-cell">Duration</TableHead>
              <TableHead className="hidden sm:table-cell">Time</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  <Loader2 className="inline h-6 w-6 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : filteredCommands.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                  {search || filter !== 'all' || showFavoritesOnly
                    ? 'No commands match your filters'
                    : 'No commands recorded yet'}
                </TableCell>
              </TableRow>
            ) : (
              filteredCommands.map((cmd) => (
                <TableRow key={cmd.id}>
                  <TableCell>
                    <button
                      onClick={() => handleToggleFavorite(cmd.id, cmd.isFavorite)}
                      className="text-muted-foreground hover:text-yellow-500 transition-colors"
                      disabled={isTogglingFavorite === cmd.id}
                    >
                      {isTogglingFavorite === cmd.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : cmd.isFavorite ? (
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      ) : (
                        <StarOff className="h-4 w-4" />
                      )}
                    </button>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted rounded px-1.5 py-0.5 font-mono">
                      {cmd.command.length > 50 ? cmd.command.slice(0, 50) + '...' : cmd.command}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={STATUS_CONFIG[cmd.status].className}>
                      <StatusIcon status={cmd.status} />
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell max-w-xs truncate text-xs text-muted-foreground">
                    {cmd.errorMessage ? (
                      <span className="text-red-500">{cmd.errorMessage}</span>
                    ) : cmd.result ? (
                      <span className="truncate block">{cmd.result}</span>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="hidden lg:table-cell text-xs text-muted-foreground">
                    {cmd.durationMs ? `${(cmd.durationMs / 1000).toFixed(2)}s` : '-'}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                    {new Date(cmd.createdAt).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleReplay(cmd.id)}
                      disabled={isReplaying === cmd.id}
                      title="Replay command"
                    >
                      {isReplaying === cmd.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RotateCcw className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground text-sm">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} commands
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * limit >= total}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
