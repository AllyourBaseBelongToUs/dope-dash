'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from 'cmdk';
import {
  Pause,
  Play,
  SkipForward,
  StopCircle,
  Terminal,
  Clock,
  Command as CommandIcon
} from 'lucide-react';
import { sendCommand, type ControlCommand } from '@/api/control';
import { useDashboardStore } from '@/store/dashboardStore';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import type { Session } from '@/types';
import { cn } from '@/utils/cn';

interface CommandPaletteProps {
  sessions: Session[];
}

// Available slash commands
const SLASH_COMMANDS = [
  {
    id: 'pause',
    label: 'Pause',
    description: 'Pause the current agent',
    icon: Pause,
    shortcut: 'Space',
    command: 'pause' as ControlCommand,
  },
  {
    id: 'resume',
    label: 'Resume',
    description: 'Resume a paused agent',
    icon: Play,
    shortcut: 'R',
    command: 'resume' as ControlCommand,
  },
  {
    id: 'skip',
    label: 'Skip',
    description: 'Skip the current task',
    icon: SkipForward,
    shortcut: 'S',
    command: 'skip' as ControlCommand,
  },
  {
    id: 'stop',
    label: 'Stop',
    description: 'Stop the agent session',
    icon: StopCircle,
    shortcut: 'Esc',
    command: 'stop' as ControlCommand,
  },
];

// Parse input to detect slash command or custom feedback
function parseInput(input: string): { type: 'command' | 'feedback'; command?: ControlCommand; feedback?: string } {
  const trimmed = input.trim();

  // Check if it's a slash command
  if (trimmed.startsWith('/')) {
    const commandPart = trimmed.slice(1).toLowerCase().split(' ')[0];
    const matched = SLASH_COMMANDS.find(
      (cmd) => cmd.id === commandPart || cmd.label.toLowerCase() === commandPart
    );

    if (matched) {
      return { type: 'command', command: matched.command };
    }
  }

  // Otherwise, treat as custom feedback
  return { type: 'feedback', feedback: trimmed };
}

export function CommandPalette({ sessions }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackTimeoutSeconds] = useState(30); // FIXED: Configurable timeout
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [countdown, setCountdown] = useState<number | null>(null);

  const { updateSession, addCommandToHistory } = useDashboardStore();

  const inputRef = useRef<HTMLInputElement>(null);
  // FIXED: Use proper timeout type for browser environment
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const handleSubmitRef = useRef<(() => void) | null>(null);

  // Get active sessions (running and not stopped)
  const activeSessions = sessions.filter(
    (s) => s.status === 'running' && s.agentStatus !== 'stopped'
  );

  // Set default selected session to the first active one
  useEffect(() => {
    if (activeSessions.length > 0 && !selectedSessionId) {
      setSelectedSessionId(activeSessions[0].id);
    }
  }, [activeSessions, selectedSessionId]);

  // Register Ctrl+K / Cmd+K keyboard shortcut
  useKeyboardShortcuts(
    [
      {
        key: 'k',
        ctrlKey: true,
        handler: () => setOpen(true),
        description: 'Open command palette',
      },
    ],
    true,
    []
  );

  // Reset input when palette opens
  useEffect(() => {
    if (open) {
      setInput('');
      setError(null);
      setHistoryIndex(-1);
      setCountdown(null);
      // Focus input after animation
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  // Cleanup timeout and countdown on unmount
  useEffect(() => {
    return () => {
      // FIXED: Clear timeout properly on unmount to prevent race condition
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
    };
  }, []); // FIXED: Removed feedbackTimeout dependency - no longer needed

  // Handle input change with timeout reset for feedback
  const handleInputChange = useCallback((value: string) => {
    // FIXED: Added input validation - max length 1000 chars
    if (value.length > 1000) {
      setError('Input too long (max 1000 characters)');
      return;
    }

    setInput(value);
    setError(null);

    // Reset timeout and countdown on keystroke for feedback mode
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    setCountdown(null);

    const parsed = parseInput(value);
    if (parsed.type === 'feedback' && value.trim()) {
      // FIXED: Use configurable timeout instead of hardcoded 30 seconds
      // Start countdown at full timeout value
      setCountdown(feedbackTimeoutSeconds);

      // Start countdown interval
      countdownRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev === null || prev <= 1) {
            if (countdownRef.current) {
              clearInterval(countdownRef.current);
              countdownRef.current = null;
            }
            return null;
          }
          return prev - 1;
        });
      }, 1000);

      // Set submit timeout - use ref to call latest handleSubmit
      timeoutRef.current = setTimeout(() => {
        handleSubmitRef.current?.();
      }, feedbackTimeoutSeconds * 1000);
    }
  }, [feedbackTimeoutSeconds]);

  // Execute a slash command
  const executeCommand = useCallback(
    async (command: ControlCommand, sessionId: string) => {
      if (!sessionId) {
        setError('No active session selected');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await sendCommand(sessionId, command);

        // Add to command history in store
        addCommandToHistory(sessionId, {
          commandId: response.command_id,
          command,
          status: response.status,
          createdAt: response.created_at,
          error: response.error,
        });

        // Update agent status
        if (response.status === 'pending' || response.status === 'acknowledged') {
          switch (command) {
            case 'pause':
              updateSession(sessionId, { agentStatus: 'paused' });
              break;
            case 'resume':
              updateSession(sessionId, { agentStatus: 'running' });
              break;
            case 'stop':
              updateSession(sessionId, { agentStatus: 'stopped', status: 'cancelled' });
              break;
            case 'skip':
              // Skip doesn't change agent status
              break;
          }
        }

        // Add to local command history
        // FIXED: Only trim when exceeding 25 items to reduce array operations
        setCommandHistory((prev) => {
          const newHistory = [`/${command}`, ...prev];
          return newHistory.length > 25 ? newHistory.slice(0, 20) : newHistory;
        });

        // Close palette on success
        setOpen(false);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : `Failed to send ${command} command`;
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [addCommandToHistory, updateSession]
  );

  // Submit custom feedback (for now, we'll send it as a skip command with metadata)
  const submitFeedback = useCallback(
    async (feedback: string, sessionId: string) => {
      if (!sessionId) {
        setError('No active session selected');
        return;
      }

      if (!feedback.trim()) {
        setError('Please enter a command or feedback');
        return;
      }

      // FIXED: Input validation and sanitization
      const sanitized = feedback.trim();
      if (sanitized.length > 1000) {
        setError('Input too long (max 1000 characters)');
        return;
      }

      // Basic XSS prevention - check for dangerous patterns
      const dangerousPatterns = ['<script', 'javascript:', 'onload=', 'onerror='];
      const hasDangerousContent = dangerousPatterns.some(pattern =>
        sanitized.toLowerCase().includes(pattern)
      );
      if (hasDangerousContent) {
        setError('Input contains potentially dangerous content');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // For now, send feedback as metadata with a skip command
        // In the future, this could be a dedicated feedback command type
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8002'}/api/control/${sessionId}/command`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: 'skip',
              timeout_seconds: 60,
              metadata: { custom_feedback: sanitized },
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Failed to send feedback');
        }

        const result = await response.json();

        // Add to command history
        addCommandToHistory(sessionId, {
          commandId: result.command_id,
          command: 'skip',
          status: result.status,
          createdAt: result.created_at,
          error: result.error,
        });

        // Add to local history
        // FIXED: Only trim when exceeding 25 items to reduce array operations
        setCommandHistory((prev) => {
          const newHistory = [sanitized, ...prev];
          return newHistory.length > 25 ? newHistory.slice(0, 20) : newHistory;
        });

        setOpen(false);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to send feedback';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [addCommandToHistory]
  );

  // Handle form submission
  const handleSubmit = useCallback(() => {
    if (loading) return;

    // Clear timeout and countdown when submitting
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    setCountdown(null);

    const sessionId = selectedSessionId || activeSessions[0]?.id;
    if (!sessionId) {
      setError('No active session available');
      return;
    }

    const parsed = parseInput(input);

    if (parsed.type === 'command' && parsed.command) {
      executeCommand(parsed.command, sessionId);
    } else if (parsed.type === 'feedback' && parsed.feedback) {
      submitFeedback(parsed.feedback, sessionId);
    }
  }, [input, selectedSessionId, activeSessions, loading, executeCommand, submitFeedback]);

  // Keep ref updated with latest handleSubmit
  useEffect(() => {
    handleSubmitRef.current = handleSubmit;
  }, [handleSubmit]);

  // Handle keyboard navigation within the palette
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Handle Ctrl+Enter to submit
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmit();
        return;
      }

      // Handle up/down for command history
      // FIXED: History navigation now goes oldest (up) to newest (down)
      if (e.key === 'ArrowUp' && commandHistory.length > 0) {
        e.preventDefault();
        // Arrow Up: Go to older commands (increase index)
        const newIndex = Math.min(historyIndex + 1, commandHistory.length - 1);
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex]);
      } else if (e.key === 'ArrowDown' && historyIndex > -1) {
        e.preventDefault();
        // Arrow Down: Go to newer commands (decrease index)
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(newIndex >= 0 ? commandHistory[commandHistory.length - 1 - newIndex] : '');
      }
    },
    [commandHistory, historyIndex, handleSubmit]
  );

  const selectedSession = sessions.find((s) => s.id === selectedSessionId);
  const parsedInput = parseInput(input);

  return (
    <>
      {/* Keyboard shortcut hint */}
      <div className="fixed bottom-4 right-4 z-40">
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-md shadow-md hover:bg-muted transition-colors text-sm text-muted-foreground"
        >
          <CommandIcon className="h-4 w-4" />
          <span>Commands</span>
          <kbd className="ml-2 px-1.5 py-0.5 bg-muted text-xs font-mono rounded">Ctrl+K</kbd>
        </button>
      </div>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <div className="flex flex-col max-h-[600px]">
          {/* Session Selector */}
          {activeSessions.length > 1 && (
            <div className="flex items-center gap-2 p-4 border-b border-border">
              <span className="text-sm text-muted-foreground">Target:</span>
              <div className="flex flex-wrap gap-2">
                {activeSessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => setSelectedSessionId(session.id)}
                    className={cn(
                      'px-3 py-1 text-sm rounded-md transition-colors',
                      selectedSessionId === session.id
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted-foreground/20'
                    )}
                  >
                    {session.projectName}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4">
            <CommandInput
              ref={inputRef}
              value={input}
              onValueChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a command or feedback... (Ctrl+Enter to submit)"
              className="text-base"
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="px-4 pb-2">
              <div className="text-sm text-red-500 bg-red-950/30 border border-red-900/50 rounded-md p-2">
                {error}
              </div>
            </div>
          )}

          {/* Feedback timeout indicator with countdown */}
          {parsedInput.type === 'feedback' && input.trim() && !loading && countdown !== null && (
            <div className="px-4 pb-2">
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Auto-submit in <span className={cn(
                  "font-mono font-semibold",
                  countdown <= 5 ? "text-red-500" : countdown <= 10 ? "text-yellow-500" : ""
                )}>{countdown}s</span> (type to reset)
              </div>
              {/* Progress bar */}
              <div className="mt-1 h-1 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full transition-all duration-300 ease-out",
                    countdown <= 5 ? "bg-red-500" : countdown <= 10 ? "bg-yellow-500" : "bg-primary"
                  )}
                  style={{ width: `${(countdown / feedbackTimeoutSeconds) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Command List */}
          <CommandList className="flex-1 overflow-y-auto px-4 pb-4">
            <CommandEmpty>No results found.</CommandEmpty>

            {/* Session info */}
            {selectedSession && (
              <div className="py-2 text-sm text-muted-foreground">
                <span className="font-medium">{selectedSession.projectName}</span>
                {' '}
                <span className={cn(
                  'capitalize',
                  selectedSession.agentStatus === 'running' && 'text-blue-500',
                  selectedSession.agentStatus === 'paused' && 'text-yellow-500',
                  selectedSession.agentStatus === 'stopped' && 'text-red-500'
                )}>
                  {selectedSession.agentStatus || 'running'}
                </span>
              </div>
            )}

            <CommandGroup heading="Slash Commands">
              {SLASH_COMMANDS.map((cmd) => {
                const Icon = cmd.icon;
                const isDisabled =
                  (cmd.command === 'pause' && selectedSession?.agentStatus === 'paused') ||
                  (cmd.command === 'resume' && selectedSession?.agentStatus !== 'paused') ||
                  (cmd.command === 'stop' && selectedSession?.agentStatus === 'stopped') ||
                  (selectedSession?.agentStatus === 'stopped');

                return (
                  <CommandItem
                    key={cmd.id}
                    value={`/${cmd.id}`}
                    onSelect={() => !isDisabled && executeCommand(cmd.command, selectedSessionId || activeSessions[0]?.id)}
                    disabled={isDisabled}
                    className={cn(
                      'flex items-center gap-3',
                      isDisabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <div className="flex-1">
                      <div className="font-medium">{cmd.label}</div>
                      <div className="text-xs text-muted-foreground">{cmd.description}</div>
                    </div>
                    <kbd className="px-1.5 py-0.5 bg-muted text-xs font-mono rounded">
                      {cmd.shortcut}
                    </kbd>
                  </CommandItem>
                );
              })}
            </CommandGroup>

            <CommandSeparator />

            <CommandGroup heading="Custom Feedback">
              <CommandItem
                value="feedback"
                onSelect={() => {
                  if (input.trim()) {
                    handleSubmit();
                  }
                }}
                disabled={!input.trim() || loading}
                className={cn(
                  'flex items-center gap-3',
                  (!input.trim() || loading) && 'opacity-50 cursor-not-allowed'
                )}
              >
                <Terminal className="h-4 w-4" />
                <div className="flex-1">
                  <div className="font-medium">Send Custom Feedback</div>
                  <div className="text-xs text-muted-foreground">
                    {input.trim() ? `"${input.slice(0, 50)}${input.length > 50 ? '...' : ''}"` : 'Type your feedback above'}
                  </div>
                </div>
                <kbd className="px-1.5 py-0.5 bg-muted text-xs font-mono rounded">Ctrl+Enter</kbd>
              </CommandItem>
            </CommandGroup>

            {/* Command History */}
            {commandHistory.length > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup heading="Recent Commands">
                  {commandHistory.slice(0, 5).map((cmd, idx) => (
                    <CommandItem
                      key={idx}
                      value={`history-${idx}`}
                      onSelect={() => {
                        setInput(cmd);
                        inputRef.current?.focus();
                      }}
                      className="flex items-center gap-3"
                    >
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{cmd}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>

          {/* Footer with keyboard hints */}
          <div className="p-3 border-t border-border text-xs text-muted-foreground flex items-center justify-between">
            <div className="flex gap-4">
              <span><kbd className="font-mono bg-muted px-1 rounded">↑↓</kbd> History</span>
              <span><kbd className="font-mono bg-muted px-1 rounded">Ctrl+Enter</kbd> Submit</span>
              <span><kbd className="font-mono bg-muted px-1 rounded">Esc</kbd> Close</span>
            </div>
            {loading && (
              <span className="text-primary">Sending...</span>
            )}
          </div>
        </div>
      </CommandDialog>
    </>
  );
}
