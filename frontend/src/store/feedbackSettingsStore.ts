import { create } from 'zustand';

export interface FeedbackSettings {
  enabled: boolean;
  wsUrl: string;
  timeout: number;
  fallbackToLocal: boolean;
  showNotifications: boolean;
}

interface FeedbackSettingsStore {
  settings: FeedbackSettings;
  updateSettings: (updates: Partial<FeedbackSettings>) => void;
  resetToDefaults: () => void;
}

const defaultSettings: FeedbackSettings = {
  enabled: true,
  // Step-5 port spacing: WebSocket on 8005
  wsUrl: 'ws://localhost:8005/feedback/ws/mcp',
  timeout: 300, // 5 minutes
  fallbackToLocal: true,
  showNotifications: true,
};

const STORAGE_KEY = 'feedback-settings';

// Load settings from localStorage
const loadSettings = (): FeedbackSettings => {
  if (typeof window === 'undefined') {
    return defaultSettings;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.error('[FeedbackSettingsStore] Failed to load settings:', error);
  }

  return defaultSettings;
};

// Save settings to localStorage
const saveSettings = (settings: FeedbackSettings): void => {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('[FeedbackSettingsStore] Failed to save settings:', error);
  }
};

export const useFeedbackSettingsStore = create<FeedbackSettingsStore>((set, get) => ({
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
