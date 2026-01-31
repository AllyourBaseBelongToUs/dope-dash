import { useEffect, useRef, useCallback, useState } from 'react';
import type { WebSocketMessage } from '@/types';

interface UsePollingOptions {
  apiUrl: string;
  interval?: number;
  enabled?: boolean;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Error) => void;
}

interface UsePollingReturn {
  isActive: boolean;
  lastPollTime: Date | null;
  error: string | null;
  manualPoll: () => Promise<void>;
}

export function usePolling({
  apiUrl,
  interval = 5000,
  enabled = true,
  onMessage,
  onError,
}: UsePollingOptions): UsePollingReturn {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [lastPollTime, setLastPollTime] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const processedEventIds = useRef<Set<string>>(new Set());

  const poll = useCallback(async () => {
    try {
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const events: WebSocketMessage[] = await response.json();

      // Process only new events (deduplication)
      events.forEach((event) => {
        if (event.id && !processedEventIds.current.has(event.id)) {
          processedEventIds.current.add(event.id);
          onMessage?.(event);
        }
      });

      setLastPollTime(new Date());
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
    }
  }, [apiUrl, onMessage, onError]);

  const manualPoll = useCallback(async () => {
    await poll();
  }, [poll]);

  const startPolling = useCallback(() => {
    setIsActive(true);
    poll(); // Initial poll

    intervalRef.current = setInterval(() => {
      poll();
    }, interval);
  }, [poll, interval]);

  const stopPolling = useCallback(() => {
    setIsActive(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      startPolling();
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling]);

  return {
    isActive,
    lastPollTime,
    error,
    manualPoll,
  };
}
