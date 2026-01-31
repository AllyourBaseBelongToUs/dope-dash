import { useEffect, useRef } from 'react';
import { useEnvironmentStore } from '@/store/environmentStore';
import { checkNetworkAvailability } from '@/utils/detectEnvironment';

interface UseNetworkMonitoringOptions {
  onNetworkChange?: (isOnline: boolean) => void;
  onEnvironmentChange?: () => void;
  checkInterval?: number;
}

export function useNetworkMonitoring({
  onNetworkChange,
  onEnvironmentChange,
  checkInterval = 30000, // Check every 30 seconds
}: UseNetworkMonitoringOptions = {}) {
  const detectEnvironment = useEnvironmentStore((state) => state.detectEnvironment);
  const currentEnv = useEnvironmentStore((state) => state.current);
  const previousEnvRef = useRef<typeof currentEnv>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Handle browser online/offline events
    const handleOnline = () => {
      console.info('[Network] Connection restored');
      onNetworkChange?.(true);

      // Re-detect environment when coming back online
      detectEnvironment();
    };

    const handleOffline = () => {
      console.warn('[Network] Connection lost');
      onNetworkChange?.(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set up periodic network and environment checks
    intervalRef.current = setInterval(async () => {
      const isOnline = await checkNetworkAvailability();

      if (isOnline) {
        // Check if environment has changed
        const newEnv = detectEnvironment();

        if (newEnv && previousEnvRef.current?.type !== newEnv.type) {
          console.info('[Network] Environment changed during periodic check');
          onEnvironmentChange?.();
        }

        previousEnvRef.current = newEnv;
      } else {
        onNetworkChange?.(false);
      }
    }, checkInterval);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);

      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [detectEnvironment, onNetworkChange, onEnvironmentChange, checkInterval]);

  return {
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    currentEnv,
  };
}
