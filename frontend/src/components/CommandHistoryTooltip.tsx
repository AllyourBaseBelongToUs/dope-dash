'use client';

import * as Tooltip from '@radix-ui/react-tooltip';
import { Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import type { DashboardCommandEntry } from '@/types';

interface CommandHistoryTooltipProps {
  history: DashboardCommandEntry[];
  children: React.ReactNode;
}

function getStatusIcon(status: DashboardCommandEntry['status']) {
  switch (status) {
    case 'pending':
      return <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />;
    case 'acknowledged':
      return <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="h-3 w-3 text-green-500" />;
    case 'failed':
      return <XCircle className="h-3 w-3 text-red-500" />;
    case 'timeout':
      return <XCircle className="h-3 w-3 text-orange-500" />;
    default:
      return <Clock className="h-3 w-3 text-muted-foreground" />;
  }
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);

  if (diffSecs < 60) {
    return `${diffSecs}s ago`;
  } else if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}

export function CommandHistoryTooltip({ history, children }: CommandHistoryTooltipProps) {
  const recentHistory = history.slice(-5).reverse(); // Show last 5, most recent first

  return (
    <Tooltip.Root delayDuration={300}>
      <Tooltip.Trigger asChild>
        {children}
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          className="z-50 max-w-sm bg-card border border-border rounded-lg shadow-lg p-3 data-[state=delayed-open]:data-[side=top]:animate-slideDownAndFade data-[state=delayed-open]:data-[side=right]:animate-slideLeftAndFade data-[state=delayed-open]:data-[side=bottom]:animate-slideUpAndFade data-[state=delayed-open]:data-[side=left]:animate-slideRightAndFade"
          sideOffset={8}
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-foreground border-b border-border pb-2">
              <Clock className="h-3.5 w-3.5" />
              <span>Command History</span>
            </div>

            {recentHistory.length === 0 ? (
              <p className="text-xs text-muted-foreground py-1">No commands sent yet</p>
            ) : (
              <ul className="space-y-1.5">
                {recentHistory.map((entry) => (
                  <li
                    key={entry.commandId}
                    className="flex items-center gap-2 text-xs group"
                  >
                    <div className="flex-shrink-0">
                      {getStatusIcon(entry.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground capitalize">
                          {entry.command}
                        </span>
                        <span className="text-muted-foreground text-[10px]">
                          {formatTime(entry.createdAt)}
                        </span>
                      </div>
                      {entry.error && (
                        <p className="text-red-400 text-[10px] mt-0.5 truncate">
                          {entry.error}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Tooltip.Arrow className="fill-border" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
