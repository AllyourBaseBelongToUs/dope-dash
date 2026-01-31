import type { NotificationSettings } from '@/types';
import type { ConnectionSettings } from '@/store/connectionSettingsStore';

/**
 * Complete settings structure for export/import
 */
export interface DopeDashSettings {
  version: string;
  exportedAt: string;
  settings: {
    notifications: NotificationSettings;
    connections: ConnectionSettings;
  };
}

/**
 * Schema for validating imported settings
 */
const SETTINGS_SCHEMA = {
  version: 'string',
  exportedAt: 'string',
  settings: {
    notifications: {
      soundEnabled: 'boolean',
      preferences: 'string',
      desktopEnabled: 'boolean',
    },
    connections: {
      wsUrl: 'string',
      apiUrl: 'string',
      controlApiUrl: 'string',
      analyticsApiUrl: 'string',
    },
  },
};

/**
 * Default connection settings (from connectionSettingsStore)
 */
const DEFAULT_CONNECTION_SETTINGS: ConnectionSettings = {
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws',
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/events',
  controlApiUrl: process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8002',
  analyticsApiUrl: process.env.NEXT_PUBLIC_ANALYTICS_API_URL || 'http://localhost:8004',
};

/**
 * Validate settings object against schema
 */
function validateSettings(obj: unknown): obj is DopeDashSettings {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const settings = obj as Record<string, unknown>;

  // Check version
  if (typeof settings.version !== 'string') {
    return false;
  }

  // Check exportedAt
  if (typeof settings.exportedAt !== 'string') {
    return false;
  }

  // Check settings object
  if (typeof settings.settings !== 'object' || settings.settings === null) {
    return false;
  }

  const settingsObj = settings.settings as Record<string, unknown>;

  // Validate notifications
  if (typeof settingsObj.notifications !== 'object' || settingsObj.notifications === null) {
    return false;
  }

  const notifications = settingsObj.notifications as Record<string, unknown>;
  if (
    typeof notifications.soundEnabled !== 'boolean' ||
    typeof notifications.desktopEnabled !== 'boolean' ||
    typeof notifications.preferences !== 'string'
  ) {
    return false;
  }

  // Validate connections
  if (typeof settingsObj.connections !== 'object' || settingsObj.connections === null) {
    return false;
  }

  const connections = settingsObj.connections as Record<string, unknown>;
  if (
    typeof connections.wsUrl !== 'string' ||
    typeof connections.apiUrl !== 'string' ||
    typeof connections.controlApiUrl !== 'string' ||
    typeof connections.analyticsApiUrl !== 'string'
  ) {
    return false;
  }

  return true;
}

/**
 * Export all settings as JSON
 */
export function exportSettings(
  notificationSettings: NotificationSettings,
  connectionSettings: ConnectionSettings
): string {
  const settings: DopeDashSettings = {
    version: '0.1.0',
    exportedAt: new Date().toISOString(),
    settings: {
      notifications: notificationSettings,
      connections: connectionSettings,
    },
  };

  return JSON.stringify(settings, null, 2);
}

/**
 * Download settings as JSON file
 */
export function downloadSettings(settings: string): void {
  const blob = new Blob([settings], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `dope-dash-settings-${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Parse and validate imported settings
 */
export function parseImportedSettings(jsonString: string): {
  success: boolean;
  settings?: DopeDashSettings;
  error?: string;
} {
  try {
    const parsed = JSON.parse(jsonString);

    if (!validateSettings(parsed)) {
      return {
        success: false,
        error: 'Invalid settings format. Please ensure the file is a valid Dope Dash settings export.',
      };
    }

    // Check version compatibility
    if (parsed.version !== '0.1.0') {
      return {
        success: false,
        error: `Settings version ${parsed.version} is not supported. Current version: 0.1.0`,
      };
    }

    return {
      success: true,
      settings: parsed,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to parse JSON file',
    };
  }
}

/**
 * Get default connection settings
 */
export function getDefaultConnectionSettings(): ConnectionSettings {
  return { ...DEFAULT_CONNECTION_SETTINGS };
}

/**
 * Read file as text
 */
export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) {
        resolve(e.target.result as string);
      } else {
        reject(new Error('Failed to read file'));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
