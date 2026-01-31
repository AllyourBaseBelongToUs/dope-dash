import type { ConnectionStatus } from '@/types';

interface ConnectionStatusProps {
  status: ConnectionStatus;
}

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          label: 'Connected',
          color: 'bg-green-500',
          textColor: 'text-green-500',
          pulse: true,
        };
      case 'connecting':
        return {
          label: 'Connecting...',
          color: 'bg-yellow-500',
          textColor: 'text-yellow-500',
          pulse: true,
        };
      case 'polling':
        return {
          label: 'Polling',
          color: 'bg-blue-500',
          textColor: 'text-blue-500',
          pulse: false,
        };
      case 'disconnected':
      default:
        return {
          label: 'Disconnected',
          color: 'bg-red-500',
          textColor: 'text-red-500',
          pulse: false,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1.5">
        <span className={`relative flex h-2.5 w-2.5`}>
          <span
            className={`${config.color} inline-flex rounded-full opacity-100 ${config.pulse ? 'animate-ping' : ''}`}
          />
          <span
            className={`${config.color} relative inline-flex rounded-full h-2.5 w-2.5`}
          />
        </span>
        <span className={`text-sm font-medium ${config.textColor}`}>
          {config.label}
        </span>
      </div>
    </div>
  );
}
