'use client';

import { ReactNode } from 'react';
import { Navigation } from './Navigation';

interface AppShellProps {
  children: ReactNode;
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  sessionCount?: number;
  agentCount?: number;
}

export function AppShell({
  children,
  title,
  subtitle,
  icon,
  actions,
  sessionCount,
  agentCount,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Navigation Bar */}
      <Navigation sessionCount={sessionCount} agentCount={agentCount} />

      {/* Page Header */}
      <header className="border-b border-border bg-card/30">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {icon && (
                <div className="bg-primary/10 p-2 rounded-lg">
                  {icon}
                </div>
              )}
              <div>
                <h1 className="text-xl font-bold text-foreground">{title}</h1>
                {subtitle && (
                  <p className="text-xs" style={{ color: 'var(--font-color)' }}>{subtitle}</p>
                )}
              </div>
            </div>
            {actions && (
              <div className="flex items-center gap-2">
                {actions}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-auto">
        <div className="container mx-auto px-4 py-3">
          <p className="text-xs text-center" style={{ color: 'var(--font-color)' }}>
            Dope Dash - Real-time multi-agent control center
          </p>
        </div>
      </footer>
    </div>
  );
}
