'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Star,
  Clock,
  Terminal,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CommandTemplate } from '@/types';
import { getCommandService } from '@/services/commandService';

interface CommandDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId?: string;
  sessionId?: string;
  onCommandSent?: (command: string) => void;
}

interface CommandCategory {
  name: string;
  templates: CommandTemplate[];
}

const DEFAULT_TEMPLATES: CommandTemplate[] = [
  {
    id: 't-1',
    name: 'List Files',
    description: 'List all files in the current directory',
    command: 'ls -la',
    category: 'files',
    tags: ['list', 'files'],
  },
  {
    id: 't-2',
    name: 'Git Status',
    description: 'Show git repository status',
    command: 'git status',
    category: 'git',
    tags: ['git', 'status'],
  },
  {
    id: 't-3',
    name: 'Git Log',
    description: 'Show recent git commits',
    command: 'git log --oneline -10',
    category: 'git',
    tags: ['git', 'log', 'history'],
  },
  {
    id: 't-4',
    name: 'Process List',
    description: 'List running processes',
    command: 'ps aux',
    category: 'system',
    tags: ['processes', 'system'],
  },
  {
    id: 't-5',
    name: 'Disk Usage',
    description: 'Check disk usage',
    command: 'df -h',
    category: 'system',
    tags: ['disk', 'storage'],
  },
  {
    id: 't-6',
    name: 'Memory Usage',
    description: 'Check memory usage',
    command: 'free -h',
    category: 'system',
    tags: ['memory', 'ram'],
  },
  {
    id: 't-7',
    name: 'Network Connections',
    description: 'List network connections',
    command: 'netstat -tuln',
    category: 'network',
    tags: ['network', 'connections'],
  },
  {
    id: 't-8',
    name: 'Test Connection',
    description: 'Test network connectivity to a host',
    command: 'ping -c 4 {{host}}',
    category: 'network',
    tags: ['ping', 'network', 'test'],
  },
  {
    id: 't-9',
    name: 'Find Files',
    description: 'Find files by name pattern',
    command: 'find . -name \'{{pattern}}\' -type f',
    category: 'files',
    tags: ['find', 'search', 'files'],
  },
  {
    id: 't-10',
    name: 'Grep Search',
    description: 'Search for text in files',
    command: 'grep -r \'{{search_term}}\' .',
    category: 'search',
    tags: ['grep', 'search', 'text'],
  },
];

export function CommandDialog({
  open,
  onOpenChange,
  projectId,
  sessionId,
  onCommandSent,
}: CommandDialogProps) {
  const [input, setInput] = React.useState('');
  const [templates, setTemplates] = React.useState<CommandTemplate[]>(DEFAULT_TEMPLATES);
  const [recentCommands, setRecentCommands] = React.useState<string[]>([]);
  const [favoriteCommands, setFavoriteCommands] = React.useState<string[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSending, setIsSending] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState<'type' | 'templates' | 'history' | 'favorites'>('type');

  const inputRef = React.useRef<HTMLInputElement>(null);
  const commandService = getCommandService();

  // Load data when dialog opens
  React.useEffect(() => {
    if (open) {
      loadData();
      // Focus input after a short delay
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setInput('');
      setActiveTab('type');
    }
  }, [open, projectId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load recent commands
      const recent = await commandService.getRecentCommands(projectId, 10);
      setRecentCommands(recent);

      // Load favorite commands
      const favResponse = await commandService.getFavoriteCommands(projectId, 10);
      setFavoriteCommands(favResponse.commands.map((c) => c.command));

      // Load templates from server
      const serverTemplates = await commandService.getCommandTemplates();
      if (serverTemplates.length > 0) {
        setTemplates(serverTemplates);
      }
    } catch (error) {
      console.error('Failed to load command data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const categories = React.useMemo(() => {
    const grouped: Record<string, CommandTemplate[]> = {};
    templates.forEach((template) => {
      if (!grouped[template.category]) {
        grouped[template.category] = [];
      }
      grouped[template.category].push(template);
    });
    return Object.entries(grouped).map(([name, templates]) => ({
      name,
      templates,
    }));
  }, [templates]);

  const handleSelectTemplate = (template: CommandTemplate) => {
    setInput(template.command);
    inputRef.current?.focus();
  };

  const handleSelectRecent = (command: string) => {
    setInput(command);
    inputRef.current?.focus();
  };

  const handleSelectFavorite = (command: string) => {
    setInput(command);
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    if (!input.trim() || isSending) {
      return;
    }

    setIsSending(true);
    try {
      await commandService.sendCommand({
        command: input.trim(),
        projectId,
        sessionId,
        templateName: templates.find((t) => t.command === input)?.name,
      });

      onCommandSent?.(input.trim());
      onOpenChange(false);

      // Reload data
      await loadData();
    } catch (error) {
      console.error('Failed to send command:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === 'Escape') {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl gap-0 p-0">
        <DialogHeader className="border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="h-5 w-5 text-primary" />
              <DialogTitle>Send Custom Command</DialogTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActiveTab('templates')}
              className={cn(activeTab === 'templates' && 'bg-accent')}
            >
              Templates
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActiveTab('history')}
              className={cn(activeTab === 'history' && 'bg-accent')}
            >
              <Clock className="mr-1 h-3 w-3" />
              History
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActiveTab('favorites')}
              className={cn(activeTab === 'favorites' && 'bg-accent')}
            >
              <Star className="mr-1 h-3 w-3" />
              Favorites
            </Button>
          </div>
          <DialogDescription>
            {projectId ? 'Send a command to this project' : 'Send a custom command'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex">
          {/* Main content area */}
          <div className="flex-1">
            {/* Input area */}
            <div className="border-b p-4">
              <div className="relative">
                <Terminal className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command or search templates..."
                  className="pl-10 pr-12 font-mono"
                  autoFocus
                />
                <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
                  <kbd className="text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded border px-1.5 py-0.5 text-xs font-mono">
                    Enter
                  </kbd>
                  <span className="text-muted-foreground text-xs">to send</span>
                </div>
              </div>
            </div>

            {/* Suggestions/Templates */}
            <div className="h-[300px] overflow-y-auto">
              {isLoading ? (
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="p-2">
                  {activeTab === 'templates' &&
                    categories.map((category) => (
                      <div key={category.name} className="mb-4">
                        <div className="mb-2 flex items-center gap-2 px-2 text-xs font-semibold uppercase text-muted-foreground">
                          <ChevronRight className="h-3 w-3" />
                          {category.name}
                        </div>
                        {category.templates.map((template) => (
                          <button
                            key={template.id}
                            onClick={() => handleSelectTemplate(template)}
                            className="hover:bg-accent flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors"
                          >
                            <div>
                              <div className="font-medium">{template.name}</div>
                              <div className="text-muted-foreground text-xs">
                                {template.description}
                              </div>
                            </div>
                            <code className="text-muted-foreground bg-muted rounded px-1.5 py-0.5 text-xs">
                              {template.command}
                            </code>
                          </button>
                        ))}
                      </div>
                    ))}

                  {activeTab === 'history' &&
                    (recentCommands.length > 0 ? (
                      recentCommands.map((command, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSelectRecent(command)}
                          className="hover:bg-accent flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors"
                        >
                          <Clock className="mt-0.5 h-3 w-3 text-muted-foreground" />
                          <code className="font-mono text-xs">{command}</code>
                        </button>
                      ))
                    ) : (
                      <div className="text-muted-foreground px-3 py-8 text-center text-sm">
                        No recent commands found
                      </div>
                    ))}

                  {activeTab === 'favorites' &&
                    (favoriteCommands.length > 0 ? (
                      favoriteCommands.map((command, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSelectFavorite(command)}
                          className="hover:bg-accent flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors"
                        >
                          <Star className="mt-0.5 h-3 w-3 fill-yellow-400 text-yellow-400" />
                          <code className="font-mono text-xs">{command}</code>
                        </button>
                      ))
                    ) : (
                      <div className="text-muted-foreground px-3 py-8 text-center text-sm">
                        No favorite commands yet. Star a command to add it here.
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="border-t px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSending}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={!input.trim() || isSending}>
            {isSending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Terminal className="mr-2 h-4 w-4" />
                Send Command
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
