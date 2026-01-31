import type { AgentStatus } from '@/types';
import { cn } from '@/utils/cn';

interface StatusBadgeProps {
  status: AgentStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    running: {
      label: 'Running',
      color: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
      dotColor: 'bg-blue-500 animate-pulse',
    },
    paused: {
      label: 'Paused',
      color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
      dotColor: 'bg-yellow-500',
    },
    stopped: {
      label: 'Stopped',
      color: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
      dotColor: 'bg-gray-500',
    },
  };

  const { label, color, dotColor } = config[status];

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium',
        color,
        className
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dotColor)} />
      {label}
    </div>
  );
}
