'use client';

import { useState, useCallback, useRef } from 'react';
import { ControlButton } from './ControlButton';
import { StopConfirmationModal } from './StopConfirmationModal';
import { AgentStatusBadge } from './AgentStatusBadge';
import * as Tooltip from '@radix-ui/react-tooltip';
import { sendCommand, type ControlCommand } from '@/api/control';
import { useDashboardStore } from '@/store/dashboardStore';
import { useAgentControlShortcuts } from '@/hooks/useKeyboardShortcuts';
import type { Session } from '@/types';
import { cn } from '@/utils/cn';

interface ControlButtonsProps {
  session: Session;
  className?: string;
}

export function ControlButtons({ session, className }: ControlButtonsProps) {
  const { updateSession, addCommandToHistory, updateCommandInHistory } = useDashboardStore();
  const [loadingCommand, setLoadingCommand] = useState<ControlCommand | null>(null);
  const [showStopModal, setShowStopModal] = useState(false);
  const [commandError, setCommandError] = useState<string | null>(null);

  const isSessionActive = session.status === 'running';
  const isAgentPaused = session.agentStatus === 'paused';
  const isAgentStopped = session.agentStatus === 'stopped';

  // Debounce command execution to prevent rapid clicks
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  const executeCommand = useCallback(
    async (command: ControlCommand) => {
      // Clear existing timer
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }

      // Debounce: wait 300ms before executing
      debounceTimer.current = setTimeout(async () => {
        setLoadingCommand(command);
        setCommandError(null);

        try {
          const response = await sendCommand(session.id, command);

          // Add command to history
          addCommandToHistory(session.id, {
            commandId: response.command_id,
            command,
            status: response.status,
            createdAt: response.created_at,
            error: response.error,
          });

          // Update agent status based on command
          if (response.status === 'pending' || response.status === 'acknowledged') {
            switch (command) {
              case 'pause':
                updateSession(session.id, { agentStatus: 'paused' });
                break;
              case 'resume':
                updateSession(session.id, { agentStatus: 'running' });
                break;
              case 'stop':
                updateSession(session.id, { agentStatus: 'stopped', status: 'cancelled' });
                break;
              case 'skip':
                // Skip doesn't change agent status
                break;
            }
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to send command';
          setCommandError(errorMessage);
          // Auto-clear error after 3 seconds
          setTimeout(() => setCommandError(null), 3000);
        } finally {
          setLoadingCommand(null);
        }
      }, 300);
    },
    [session.id, updateSession, addCommandToHistory]
  );

  // Command handlers
  const handlePause = () => executeCommand('pause');
  const handleResume = () => executeCommand('resume');
  const handleSkip = () => executeCommand('skip');
  const handleStop = () => setShowStopModal(true);
  const handleStopConfirm = () => executeCommand('stop');

  // Keyboard shortcuts (only enabled when session is active)
  useAgentControlShortcuts(
    handlePause,
    handleResume,
    handleSkip,
    handleStop,
    isSessionActive && !loadingCommand
  );

  // Generate tooltip content for command history
  const getTooltipContent = () => {
    if (!session.commandHistory || session.commandHistory.length === 0) {
      return 'No commands sent yet';
    }

    const latestCommand = session.commandHistory[session.commandHistory.length - 1];
    const timeAgo = Math.floor(
      (Date.now() - new Date(latestCommand.createdAt).getTime()) / 1000
    );

    let timeText: string;
    if (timeAgo < 60) timeText = `${timeAgo}s ago`;
    else if (timeAgo < 3600) timeText = `${Math.floor(timeAgo / 60)}m ago`;
    else timeText = `${Math.floor(timeAgo / 3600)}h ago`;

    return (
      <div className="text-xs">
        <div className="font-medium">Last Command:</div>
        <div className="capitalize">{latestCommand.command}</div>
        <div className="text-muted-foreground capitalize">{latestCommand.status}</div>
        <div className="text-muted-foreground">{timeText}</div>
      </div>
    );
  };

  return (
    <>
      <div className={cn('space-y-3', className)}>
        {/* Status Badge and Error Feedback */}
        <div className="flex items-center justify-between">
          <AgentStatusBadge status={session.agentStatus || 'running'} />
          {commandError && (
            <span className="text-xs text-red-500 flex items-center gap-1">
              <span>⚠️</span>
              {commandError}
            </span>
          )}
        </div>

        {/* Control Buttons with Tooltip */}
        <Tooltip.Provider delayDuration={300}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <div className="flex flex-wrap gap-2">
                <ControlButton
                  command="pause"
                  disabled={!isSessionActive || isAgentPaused || isAgentStopped}
                  loading={loadingCommand === 'pause'}
                  onClick={handlePause}
                />
                <ControlButton
                  command="resume"
                  disabled={!isSessionActive || !isAgentPaused || isAgentStopped}
                  loading={loadingCommand === 'resume'}
                  onClick={handleResume}
                />
                <ControlButton
                  command="skip"
                  disabled={!isSessionActive || isAgentStopped}
                  loading={loadingCommand === 'skip'}
                  onClick={handleSkip}
                />
                <ControlButton
                  command="stop"
                  disabled={!isSessionActive || isAgentStopped}
                  loading={loadingCommand === 'stop'}
                  onClick={handleStop}
                />
              </div>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="z-50 overflow-hidden rounded-md border border-border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
                sideOffset={4}
              >
                {getTooltipContent()}
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>

        {/* Keyboard shortcuts hint */}
        {isSessionActive && (
          <div className="text-xs text-muted-foreground">
            Keyboard: <kbd className="font-mono bg-muted px-1 rounded">Space</kbd> pause,
            <kbd className="font-mono bg-muted px-1 rounded ml-1">R</kbd> resume,
            <kbd className="font-mono bg-muted px-1 rounded ml-1">S</kbd> skip,
            <kbd className="font-mono bg-muted px-1 rounded ml-1">Esc</kbd> stop
          </div>
        )}
      </div>

      {/* Stop Confirmation Modal */}
      <StopConfirmationModal
        isOpen={showStopModal}
        onClose={() => setShowStopModal(false)}
        onConfirm={handleStopConfirm}
        projectName={session.projectName}
      />
    </>
  );
}
