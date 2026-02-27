'use client';

import { useState, useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { usePolling } from '@/hooks/usePolling';
import { useNetworkMonitoring } from '@/hooks/useNetworkMonitoring';
import { useNotificationStore } from '@/store/notificationStore';
import { useEnvironmentStore } from '@/store/environmentStore';
import { AppShell } from '@/components/AppShell';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { EnvironmentBadge } from '@/components/EnvironmentBadge';
import { SessionCard } from '@/components/SessionCard';
import { EventLog } from '@/components/EventLog';
import { ErrorNotifications } from '@/components/ErrorNotifications';
import { CommandPalette } from '@/components/CommandPalette';
import { NotificationPreferences } from '@/components/NotificationPreferences';
import { SoundToggleButton } from '@/components/SoundToggleButton';
import { NotificationHistory } from '@/components/NotificationHistory';
import { Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

export default function Home() {
  const {
    sessions,
    events,
    connectionStatus,
    activeSessionId,
    processMessage,
    setConnectionStatus,
    setError,
  } = useDashboardStore();

  const { initialize } = useNotificationStore();
  const environmentConfig = useEnvironmentStore((state) => state.config);
  const detectEnvironment = useEnvironmentStore((state) => state.detectEnvironment);
  const [showNotificationHistory, setShowNotificationHistory] = useState(false);

  // Detect environment on mount
  useEffect(() => {
    detectEnvironment();
  }, [detectEnvironment]);

  // Get WebSocket and API URLs from environment config
  const WS_URL = environmentConfig?.wsUrl || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws';
  const API_URL = environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/events';

  // Network monitoring for environment changes
  useNetworkMonitoring({
    onNetworkChange: (isOnline) => {
      if (!isOnline) {
        console.info('[Dashboard] Network unavailable, will use polling fallback');
      }
    },
    onEnvironmentChange: () => {
      // Force re-render to pick up new config
      console.info('[Dashboard] Environment changed, reconnecting with new config');
    },
  });

  // Initialize notification service on first user interaction
  useEffect(() => {
    const handleUserInteraction = async () => {
      await initialize();
      window.removeEventListener('click', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
    };
    window.addEventListener('click', handleUserInteraction);
    window.addEventListener('keydown', handleUserInteraction);
    return () => {
      window.removeEventListener('click', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
    };
  }, [initialize]);

  // WebSocket connection
  const { isConnected, connectionStatus: wsStatus, retryConnection } = useWebSocket({
    url: WS_URL,
    onMessage: processMessage,
    onConnectionChange: (connected, status) => {
      setConnectionStatus(status);
    },
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
  });

  // Polling fallback (enabled when WebSocket is polling/disconnected)
  usePolling({
    apiUrl: API_URL,
    interval: 5000,
    enabled: connectionStatus === 'polling',
    onMessage: processMessage,
    onError: (error) => {
      setError(error.message);
    },
  });

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  const pageActions = (
    <>
      <SoundToggleButton />
      <NotificationPreferences />
      <EnvironmentBadge />
      <ConnectionStatus status={connectionStatus} />
      {connectionStatus === 'polling' && (
        <Button
          variant="outline"
          size="sm"
          onClick={retryConnection}
          className="text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}
    </>
  );

  return (
    <>
      <AppShell
        title="Dope Dash"
        subtitle="Multi-Agent Control Center"
        icon={<Activity className="h-5 w-5 text-primary" />}
        actions={pageActions}
        sessionCount={sessions.length}
      >
        {/* Global Error Notifications */}
        <ErrorNotifications />

        {/* Notification History Panel */}
        <div className="mb-6">
          <Button
            variant="outline"
            size="sm"
            className="mb-4"
            onClick={() => setShowNotificationHistory(!showNotificationHistory)}
          >
            {showNotificationHistory ? <ChevronUp className="h-4 w-4 mr-2" /> : <ChevronDown className="h-4 w-4 mr-2" />}
            Notification History
          </Button>
          {showNotificationHistory && (
            <div className="border border-border rounded-lg p-4 bg-card">
              <NotificationHistory />
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sessions Panel */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                Active Sessions
              </h2>
              <span className="text-sm" style={{ color: 'var(--font-color)' }}>
                {sessions.length} {sessions.length === 1 ? 'session' : 'sessions'}
              </span>
            </div>

            {sessions.length === 0 ? (
              <div className="border border-dashed border-border rounded-lg p-8 text-center">
                <Activity className="h-12 w-12 mx-auto mb-4" style={{ color: 'var(--chart-overlay-color)' }} />
                <p style={{ color: 'var(--font-color)' }}>No active sessions</p>
                <p className="text-sm mt-1" style={{ color: 'var(--font-color)' }}>
                  Start a Ralph agent session to see progress here
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {sessions.map((session) => (
                  <SessionCard
                    key={session.id}
                    session={session}
                    isActive={session.id === activeSessionId}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Event Log Panel */}
          <div className="lg:col-span-1">
            <EventLog events={events} maxEvents={100} />
          </div>
        </div>
      </AppShell>

      {/* Command Palette */}
      <CommandPalette sessions={sessions} />
    </>
  );
}
