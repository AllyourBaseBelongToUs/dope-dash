import type { EnvironmentInfo, EnvironmentType, EnvironmentConfig } from '@/types';

// Known VM hostnames - add your VM hostnames here
const VM_HOSTNAMES = ['ralphserver', 'vm', 'devbox', 'ubuntu', 'debian'];

// Known local Windows patterns
const WINDOWS_PATTERNS = ['win32', 'windows'];

/**
 * Detect if running on a VM by checking hostname
 */
function detectVMEnvironment(hostname: string): boolean {
  const lowerHostname = hostname.toLowerCase();
  return VM_HOSTNAMES.some(pattern => lowerHostname.includes(pattern));
}

/**
 * Detect if running on local Windows
 */
function detectWindowsEnvironment(platform: string): boolean {
  const lowerPlatform = platform.toLowerCase();
  return WINDOWS_PATTERNS.some(pattern => lowerPlatform.includes(pattern));
}

/**
 * Detect environment type based on multiple factors
 */
export function detectEnvironmentType(): EnvironmentType {
  if (typeof window === 'undefined') {
    return 'unknown';
  }

  const hostname = window.location.hostname;
  const platform = navigator.platform;

  // Check if we're on a VM (accessed via known VM hostname)
  if (detectVMEnvironment(hostname)) {
    return 'vm';
  }

  // Check if we're on local Windows
  if (detectWindowsEnvironment(platform)) {
    return 'local';
  }

  // Check for localhost/127.0.0.1 access - could be either, default to local
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
    return 'local';
  }

  // Check for private IP addresses (likely VM)
  const privateIPPattern = /^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)/;
  if (privateIPPattern.test(hostname)) {
    return 'vm';
  }

  return 'local';
}

/**
 * Get comprehensive environment information
 */
export function getEnvironmentInfo(): EnvironmentInfo | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const type = detectEnvironmentType();
  const hostname = window.location.hostname;

  return {
    type,
    hostname,
    platform: navigator.platform,
    userAgent: navigator.userAgent,
    detectedAt: new Date().toISOString(),
    networkInfo: {
      isPrivateIP: /^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|localhost|127\.0\.0\.1|::1)/.test(hostname),
      isLocalhost: hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1',
    },
  };
}

/**
 * Get environment-specific configuration
 * Port mapping (step-5 spacing): 8000, 8005, 8010, 8015, 8020
 * - Core API: 8000
 * - WebSocket: 8005
 * - Control API: 8010
 * - Dashboard: 8015
 * - Analytics: 8020
 */
export function getEnvironmentConfig(envType: EnvironmentType): EnvironmentConfig {
  // Allow override via environment variables
  const envWsUrl = process.env.NEXT_PUBLIC_WS_URL;
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const envControlApiUrl = process.env.NEXT_PUBLIC_CONTROL_API_URL;

  if (envWsUrl || envApiUrl || envControlApiUrl) {
    return {
      wsUrl: envWsUrl || 'ws://localhost:8005/ws',
      apiUrl: envApiUrl || 'http://localhost:8005/api/events',
      controlApiUrl: envControlApiUrl || 'http://localhost:8010',
    };
  }

  // Default configurations based on environment
  switch (envType) {
    case 'vm':
      // On VM, connect to services on the same machine
      return {
        wsUrl: 'ws://localhost:8005/ws',
        apiUrl: 'http://localhost:8005/api/events',
        controlApiUrl: 'http://localhost:8010',
      };

    case 'local':
      // On local Windows, try to connect to VM by hostname or localhost
      const currentHostname = window.location.hostname;
      // If accessing via VM hostname, use that for WebSocket too
      if (currentHostname !== 'localhost' && currentHostname !== '127.0.0.1') {
        return {
          wsUrl: `ws://${currentHostname}:8005/ws`,
          apiUrl: `http://${currentHostname}:8005/api/events`,
          controlApiUrl: `http://${currentHostname}:8010`,
        };
      }
      // Fallback to localhost
      return {
        wsUrl: 'ws://localhost:8005/ws',
        apiUrl: 'http://localhost:8005/api/events',
        controlApiUrl: 'http://localhost:8010',
      };

    default:
      return {
        wsUrl: 'ws://localhost:8005/ws',
        apiUrl: 'http://localhost:8005/api/events',
        controlApiUrl: 'http://localhost:8010',
      };
  }
}

/**
 * Log environment changes for debugging
 */
export function logEnvironmentChange(
  previous: EnvironmentInfo | null,
  current: EnvironmentInfo
): void {
  const message = previous
    ? `Environment changed: ${previous.type} (${previous.hostname}) -> ${current.type} (${current.hostname})`
    : `Environment detected: ${current.type} (${current.hostname})`;

  console.info(`[Environment] ${message}`, {
    current,
    previous,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Check if network is available
 */
export async function checkNetworkAvailability(): Promise<boolean> {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return false;
  }

  // Check if browser reports online status
  if (!navigator.onLine) {
    return false;
  }

  // Try to fetch a small resource to verify actual connectivity
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    await fetch(window.location.href, {
      method: 'HEAD',
      cache: 'no-cache',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return true;
  } catch {
    return false;
  }
}

/**
 * Get environment display label
 */
export function getEnvironmentLabel(type: EnvironmentType): string {
  switch (type) {
    case 'vm':
      return 'VM';
    case 'local':
      return 'Local';
    default:
      return 'Unknown';
  }
}

/**
 * Get environment icon
 */
export function getEnvironmentIcon(type: EnvironmentType): string {
  switch (type) {
    case 'vm':
      return '☁️'; // or 'server'
    case 'local':
      return '💻'; // or 'laptop'
    default:
      return '❓';
  }
}
