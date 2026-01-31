import type { AgentStatus } from '@/types';
import { Activity, PauseCircle, XCircle } from 'lucide-react';

interface AgentStatusBadgeProps {
  status: AgentStatus;
  className?: string;
}

export function AgentStatusBadge({ status, className = '' }: AgentStatusBadgeProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'running':
        return {
          icon: <Activity className="h-3 w-3" />,
          label: 'Running',
          bgColor: 'bg-blue-500/10',
          textColor: 'text-blue-500',
          borderColor: 'border-blue-500/30',
          animate: true,
        };
      case 'paused':
        return {
          icon: <PauseCircle className="h-3 w-3" />,
          label: 'Paused',
          bgColor: 'bg-yellow-500/10',
          textColor: 'text-yellow-500',
          borderColor: 'border-yellow-500/30',
          animate: false,
        };
      case 'stopped':
        return {
          icon: <XCircle className="h-3 w-3" />,
          label: 'Stopped',
          bgColor: 'bg-red-500/10',
          textColor: 'text-red-500',
          borderColor: 'border-red-500/30',
          animate: false,
        };
      default:
        return {
          icon: <Activity className="h-3 w-3" />,
          label: 'Unknown',
          bgColor: 'bg-muted',
          textColor: 'text-muted-foreground',
          borderColor: 'border-border',
          animate: false,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${config.bgColor} ${config.textColor} ${config.borderColor} ${className}`}
    >
      <span className={config.animate ? 'animate-pulse' : ''}>
        {config.icon}
      </span>
      <span>{config.label}</span>
    </div>
  );
}
