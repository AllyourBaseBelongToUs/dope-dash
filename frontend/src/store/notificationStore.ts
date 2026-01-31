import { create } from 'zustand';
import type { Notification, NotificationSettings, NotificationType, NotificationPreference } from '@/types';
import { getNotificationService } from '@/services/notificationService';

interface NotificationStore {
  notifications: Notification[];
  settings: NotificationSettings;
  unreadCount: number;

  // Actions
  syncHistory: () => void;
  addNotification: (type: NotificationType, title: string, message: string, sessionId?: string) => void;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
  updateSettings: (updates: Partial<NotificationSettings>) => void;
  toggleSound: () => void;
  toggleDesktop: () => void;
  setPreference: (pref: NotificationPreference) => void;
  requestPermission: () => Promise<boolean>;
  initialize: () => Promise<void>;
}

export const useNotificationStore = create<NotificationStore>((set, get) => {
  const service = getNotificationService();

  return {
    notifications: service.getHistory(),
    settings: service.getSettings(),
    unreadCount: service.getUnreadCount(),

    syncHistory: () => {
      const svc = getNotificationService();
      set({
        notifications: svc.getHistory(),
        unreadCount: svc.getUnreadCount(),
      });
    },

    addNotification: (type, title, message, sessionId) => {
      const svc = getNotificationService();
      const notification = svc.notify(type, title, message, sessionId);

      if (notification) {
        set({
          notifications: svc.getHistory(),
          unreadCount: svc.getUnreadCount(),
        });
      }
    },

    markAsRead: (notificationId) => {
      const svc = getNotificationService();
      svc.markAsRead(notificationId);
      set({
        notifications: svc.getHistory(),
        unreadCount: svc.getUnreadCount(),
      });
    },

    markAllAsRead: () => {
      const svc = getNotificationService();
      svc.markAllAsRead();
      set({
        notifications: svc.getHistory(),
        unreadCount: svc.getUnreadCount(),
      });
    },

    clearNotifications: () => {
      const svc = getNotificationService();
      svc.clearHistory();
      set({
        notifications: [],
        unreadCount: 0,
      });
    },

    updateSettings: (updates) => {
      const svc = getNotificationService();
      svc.updateSettings(updates);
      set({ settings: svc.getSettings() });
    },

    toggleSound: () => {
      const svc = getNotificationService();
      const enabled = svc.toggleSound();
      set((state) => ({
        settings: { ...state.settings, soundEnabled: enabled },
      }));
    },

    toggleDesktop: () => {
      const svc = getNotificationService();
      const enabled = svc.toggleDesktop();
      set((state) => ({
        settings: { ...state.settings, desktopEnabled: enabled },
      }));
    },

    setPreference: (pref) => {
      const svc = getNotificationService();
      svc.setPreference(pref);
      set((state) => ({
        settings: { ...state.settings, preferences: pref },
      }));
    },

    requestPermission: async () => {
      const svc = getNotificationService();
      return await svc.requestNotificationPermission();
    },

    initialize: async () => {
      const svc = getNotificationService();
      await svc.initialize();
      set({
        settings: svc.getSettings(),
      });
    },
  };
});
