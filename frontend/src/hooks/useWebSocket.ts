import { useEffect, useRef, useCallback, useState } from 'react';
import type { WebSocketMessage } from '@/types';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnectionChange?: (connected: boolean, status: 'connected' | 'disconnected' | 'connecting' | 'polling') => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'polling';
  sendMessage: (message: Record<string, unknown>) => void;
  manualConnect: () => void;
  manualDisconnect: () => void;
  retryConnection: () => void;  // Retry connection from polling mode
}

export function useWebSocket({
  url,
  onMessage,
  onConnectionChange,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingRetryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'polling'>('disconnected');

  const updateConnectionStatus = useCallback((status: 'connected' | 'disconnected' | 'connecting' | 'polling') => {
    setConnectionStatus(status);
    setIsConnected(status === 'connected');
    onConnectionChange?.(status === 'connected', status);
  }, [onConnectionChange]);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pollingRetryTimeoutRef.current) {
      clearTimeout(pollingRetryTimeoutRef.current);
      pollingRetryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    cleanup();

    updateConnectionStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        updateConnectionStatus('connected');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          onMessage?.(message);

          // Respond to ping messages
          if (message.type === 'ping') {
            sendMessage({ type: 'pong' });
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        updateConnectionStatus('disconnected');
        wsRef.current = null;

        // Auto-reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const backoffDelay = reconnectInterval * Math.pow(2, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current++;

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, Math.min(backoffDelay, 30000)); // Cap at 30 seconds
        } else {
          // Switch to polling mode
          onConnectionChange?.(false, 'polling');

          // Schedule retry every 3 minutes while in polling mode
          pollingRetryTimeoutRef.current = setTimeout(() => {
            console.log('[WebSocket] Retrying connection from polling mode...');
            reconnectAttemptsRef.current = 0;  // Reset counter
            connect();
          }, 180000); // 3 minutes
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      updateConnectionStatus('disconnected');
    }
  }, [url, onMessage, onConnectionChange, reconnectInterval, maxReconnectAttempts, updateConnectionStatus, cleanup]);

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('Cannot send message: WebSocket is not connected');
    }
  }, []);

  const manualConnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  const manualDisconnect = useCallback(() => {
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
    cleanup();
    updateConnectionStatus('disconnected');
  }, [cleanup, updateConnectionStatus, maxReconnectAttempts]);

  const retryConnection = useCallback(() => {
    // Cancel pending retry
    if (pollingRetryTimeoutRef.current) {
      clearTimeout(pollingRetryTimeoutRef.current);
      pollingRetryTimeoutRef.current = null;
    }
    // Reset counter and try to reconnect immediately
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  // Auto-connect on mount
  useEffect(() => {
    connect();

    return () => {
      cleanup();
    };
  }, []); // Only run on mount

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    manualConnect,
    manualDisconnect,
    retryConnection,
  };
}
