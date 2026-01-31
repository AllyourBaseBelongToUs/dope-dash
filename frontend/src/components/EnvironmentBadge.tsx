'use client';

import { useEffect, useState } from 'react';
import { useEnvironmentStore } from '@/store/environmentStore';
import { cn } from '@/utils/cn';
import { Monitor, Server, HelpCircle } from 'lucide-react';
import type { EnvironmentType } from '@/types';

interface EnvironmentBadgeConfig {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  dotColor: string;
}

const ENVIRONMENT_CONFIGS: Record<EnvironmentType, EnvironmentBadgeConfig> = {
  vm: {
    label: 'VM',
    icon: Server,
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/50',
    dotColor: 'bg-purple-500',
  },
  local: {
    label: 'Local',
    icon: Monitor,
    color: 'bg-green-500/20 text-green-400 border-green-500/50',
    dotColor: 'bg-green-500',
  },
  unknown: {
    label: 'Unknown',
    icon: HelpCircle,
    color: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
    dotColor: 'bg-gray-500',
  },
};

export function EnvironmentBadge({ className }: { className?: string }) {
  const [mounted, setMounted] = useState(false);
  const environment = useEnvironmentStore((state) => state.current);
  const detectEnvironment = useEnvironmentStore((state) => state.detectEnvironment);

  // Detect environment on mount
  useEffect(() => {
    setMounted(true);
    detectEnvironment();
  }, [detectEnvironment]);

  // Don't render until mounted to avoid hydration mismatch
  if (!mounted || !environment) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-border/50">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-500 animate-pulse" />
        <span className="text-xs text-muted-foreground">Detecting...</span>
      </div>
    );
  }

  const config = ENVIRONMENT_CONFIGS[environment.type];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-colors',
        config.color,
        className
      )}
      title={`Environment: ${environment.type}\nHostname: ${environment.hostname}\nPlatform: ${environment.platform}`}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dotColor)} />
      <Icon className="h-3 w-3" />
      {config.label}
    </div>
  );
}
