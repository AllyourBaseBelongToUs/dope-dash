import { create } from 'zustand';

export interface ConnectionSettings {
  wsUrl: string;
  apiUrl: string;
  controlApiUrl: string;
  analyticsApiUrl: string;
}

interface ConnectionSettingsStore {
  settings: ConnectionSettings;
  updateSettings: (updates: Partial<ConnectionSettings>) => void;
  resetToDefaults: () => void;
}

const defaultSettings: ConnectionSettings = {
  // Step-5 port spacing: 8000, 8005, 8010, 8015, 8020
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8005/ws',
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005/api/events',
  controlApiUrl: process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8010',
  analyticsApiUrl: process.env.NEXT_PUBLIC_ANALYTICS_API_URL || 'http://localhost:8020',
};

const STORAGE_KEY = 'connection-settings';

// Load settings from localStorage
const loadSettings = (): ConnectionSettings => {
  if (typeof window === 'undefined') {
    return defaultSettings;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.error('[ConnectionSettingsStore] Failed to load settings:', error);
  }

  return defaultSettings;
};

// Save settings to localStorage
const saveSettings = (settings: ConnectionSettings): void => {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('[ConnectionSettingsStore] Failed to save settings:', error);
  }
};

export const useConnectionSettingsStore = create<ConnectionSettingsStore>((set, get) => ({
  settings: loadSettings(),

  updateSettings: (updates) => {
    const newSettings = { ...get().settings, ...updates };
    saveSettings(newSettings);
    set({ settings: newSettings });
  },

  resetToDefaults: () => {
    saveSettings(defaultSettings);
    set({ settings: defaultSettings });
  },
}));
