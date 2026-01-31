import type { NotificationType, NotificationSettings, Notification, NotificationPreference } from '@/types';

// Storage keys
const SETTINGS_STORAGE_KEY = 'dope-dash-notification-settings';
const HISTORY_STORAGE_KEY = 'dope-dash-notification-history';

// Default settings
const DEFAULT_SETTINGS: NotificationSettings = {
  soundEnabled: true,
  preferences: 'all',
  desktopEnabled: true,
};

/**
 * Notification Service
 * Handles audio alerts, browser desktop notifications, and notification history
 */
class NotificationService {
  private audioContext: AudioContext | null = null;
  private notificationPermission: NotificationPermission = 'default';
  private settings: NotificationSettings = { ...DEFAULT_SETTINGS };
  private history: Notification[] = [];

  constructor() {
    if (typeof window !== 'undefined') {
      this.loadSettings();
      this.loadHistory();
      this.initAudioContext();
      this.initNotificationPermission();
    }
  }

  /**
   * Load notification settings from localStorage
   */
  private loadSettings(): void {
    try {
      const saved = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (saved) {
        this.settings = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.warn('Failed to load notification settings:', e);
    }
  }

  /**
   * Save notification settings to localStorage with quota handling
   */
  private saveSettings(): void {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(this.settings));
    } catch (e) {
      // FIXED: Enhanced error handling with quota detection
      if (e instanceof DOMException && (
        e.name === 'QuotaExceededError' ||
        e.name === 'NS_ERROR_DOM_QUOTA_REACHED'
      )) {
        console.warn('localStorage quota exceeded, attempting cleanup...');
        this.handleQuotaExceeded();
        // Retry after cleanup
        try {
          localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(this.settings));
        } catch (retryError) {
          console.error('Failed to save settings even after cleanup:', retryError);
        }
      } else {
        console.warn('Failed to save notification settings:', e);
      }
    }
  }

  /**
   * Load notification history from localStorage
   */
  private loadHistory(): void {
    try {
      const saved = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (saved) {
        this.history = JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load notification history:', e);
    }
  }

  /**
   * Save notification history to localStorage with quota handling
   */
  private saveHistory(): void {
    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(this.history));
    } catch (e) {
      // FIXED: Enhanced error handling with quota detection
      if (e instanceof DOMException && (
        e.name === 'QuotaExceededError' ||
        e.name === 'NS_ERROR_DOM_QUOTA_REACHED'
      )) {
        console.warn('localStorage quota exceeded, trimming history...');
        // Trim history to 50 entries and retry
        this.history = this.history.slice(0, 50);
        try {
          localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(this.history));
        } catch (retryError) {
          console.error('Failed to save history even after trimming:', retryError);
        }
      } else {
        console.warn('Failed to save notification history:', e);
      }
    }
  }

  /**
   * Initialize Web Audio API
   */
  private initAudioContext(): void {
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    } catch (e) {
      console.warn('Web Audio API not supported:', e);
    }
  }

  /**
   * Initialize browser notification permission
   */
  private async initNotificationPermission(): Promise<void> {
    if ('Notification' in window) {
      this.notificationPermission = Notification.permission;
    }
  }

  /**
   * Request browser notification permission
   */
  async requestNotificationPermission(): Promise<boolean> {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      this.notificationPermission = permission;
      return permission === 'granted';
    }
    return false;
  }

  /**
   * Check if notifications should be shown based on preferences
   */
  private shouldNotify(type: NotificationType): boolean {
    if (this.settings.preferences === 'none') {
      return false;
    }
    if (this.settings.preferences === 'errors' && type !== 'error') {
      return false;
    }
    return true;
  }

  /**
   * Play a sound using Web Audio API
   */
  private playSound(type: NotificationType): void {
    if (!this.settings.soundEnabled || !this.audioContext) {
      return;
    }

    try {
      // Resume audio context if suspended (required by some browsers)
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }

      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      // Different sound patterns for different notification types
      const now = this.audioContext.currentTime;

      switch (type) {
        case 'spec_complete':
          // Pleasant ascending chime
          oscillator.frequency.setValueAtTime(523.25, now); // C5
          oscillator.frequency.setValueAtTime(659.25, now + 0.1); // E5
          oscillator.frequency.setValueAtTime(783.99, now + 0.2); // G5
          gainNode.gain.setValueAtTime(0.3, now);
          // FIXED: Removed invalid exponentialDecayTo call (AudioParam doesn't have this method)
          gainNode.gain.linearRampToValueAtTime(0.01, now + 0.4);
          oscillator.start(now);
          oscillator.stop(now + 0.4);
          break;

        case 'error':
          // Warning tone - lower, dissonant
          oscillator.frequency.setValueAtTime(200, now);
          oscillator.frequency.setValueAtTime(150, now + 0.15);
          oscillator.type = 'sawtooth';
          gainNode.gain.setValueAtTime(0.2, now);
          gainNode.gain.linearRampToValueAtTime(0.01, now + 0.3);
          oscillator.start(now);
          oscillator.stop(now + 0.3);
          break;

        case 'agent_stopped':
          // Two-beep notification
          oscillator.frequency.setValueAtTime(440, now);
          gainNode.gain.setValueAtTime(0.2, now);
          gainNode.gain.linearRampToValueAtTime(0.01, now + 0.15);
          oscillator.start(now);
          oscillator.stop(now + 0.15);

          const oscillator2 = this.audioContext.createOscillator();
          const gainNode2 = this.audioContext.createGain();
          oscillator2.connect(gainNode2);
          gainNode2.connect(this.audioContext.destination);
          oscillator2.frequency.setValueAtTime(440, now + 0.2);
          gainNode2.gain.setValueAtTime(0.2, now + 0.2);
          gainNode2.gain.linearRampToValueAtTime(0.01, now + 0.35);
          oscillator2.start(now + 0.2);
          oscillator2.stop(now + 0.35);
          break;

        default:
          // Default simple beep
          oscillator.frequency.setValueAtTime(440, now);
          gainNode.gain.setValueAtTime(0.2, now);
          gainNode.gain.linearRampToValueAtTime(0.01, now + 0.2);
          oscillator.start(now);
          oscillator.stop(now + 0.2);
      }
    } catch (e) {
      console.warn('Failed to play notification sound:', e);
    }
  }

  /**
   * Show browser desktop notification
   */
  private showDesktopNotification(type: NotificationType, title: string, message: string, sessionId?: string): void {
    if (!this.settings.desktopEnabled) {
      return;
    }

    if ('Notification' in window && this.notificationPermission === 'granted') {
      const notification = new Notification(title, {
        body: message,
        icon: '/favicon.ico',
        tag: sessionId || type,
        requireInteraction: type === 'error',
      });

      // Auto-close non-error notifications after 5 seconds
      if (type !== 'error') {
        setTimeout(() => notification.close(), 5000);
      }

      // Focus window on click
      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    }
  }

  /**
   * Generate a unique notification ID using crypto.randomUUID()
   * Falls back to timestamp + random string if crypto is not available
   */
  private generateNotificationId(type: NotificationType): string {
    try {
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
      }
    } catch (e) {
      console.warn('crypto.randomUUID() not available, falling back to timestamp + random');
    }
    // Fallback for older browsers or non-secure contexts
    return `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Trigger a notification
   */
  notify(type: NotificationType, title: string, message: string, sessionId?: string): Notification | null {
    if (!this.shouldNotify(type)) {
      return null;
    }

    // Play sound
    this.playSound(type);

    // Show desktop notification
    this.showDesktopNotification(type, title, message, sessionId);

    // Create notification object for tracking
    const notification: Notification = {
      id: this.generateNotificationId(type),
      type,
      title,
      message,
      sessionId,
      timestamp: new Date().toISOString(),
      read: false,
    };

    // Add to history
    this.addToHistory(notification);

    return notification;
  }

  /**
   * Add notification to history
   */
  private addToHistory(notification: Notification): void {
    this.history.unshift(notification);
    // Keep only last 100 notifications
    if (this.history.length > 100) {
      this.history = this.history.slice(0, 100);
    }
    this.saveHistory();
  }

  /**
   * Get current notification settings
   */
  getSettings(): NotificationSettings {
    return { ...this.settings };
  }

  /**
   * Update notification settings
   */
  updateSettings(updates: Partial<NotificationSettings>): void {
    this.settings = { ...this.settings, ...updates };
    this.saveSettings();
  }

  /**
   * Toggle sound on/off
   */
  toggleSound(): boolean {
    this.settings.soundEnabled = !this.settings.soundEnabled;
    this.saveSettings();
    return this.settings.soundEnabled;
  }

  /**
   * Toggle desktop notifications on/off
   */
  toggleDesktop(): boolean {
    this.settings.desktopEnabled = !this.settings.desktopEnabled;
    this.saveSettings();
    return this.settings.desktopEnabled;
  }

  /**
   * Set notification preference level
   */
  setPreference(pref: NotificationPreference): void {
    this.settings.preferences = pref;
    this.saveSettings();
  }

  /**
   * Check if desktop notifications are supported
   */
  isDesktopSupported(): boolean {
    return 'Notification' in window;
  }

  /**
   * Check if desktop notifications are permitted
   */
  isDesktopPermitted(): boolean {
    return this.notificationPermission === 'granted';
  }

  /**
   * Check if audio is supported
   */
  isAudioSupported(): boolean {
    return this.audioContext !== null;
  }

  /**
   * Get notification history
   */
  getHistory(limit?: number): Notification[] {
    if (limit) {
      return this.history.slice(0, limit);
    }
    return [...this.history];
  }

  /**
   * Get unread notification count
   */
  getUnreadCount(): number {
    return this.history.filter(n => !n.read).length;
  }

  /**
   * Mark notification as read
   */
  markAsRead(notificationId: string): void {
    const notification = this.history.find(n => n.id === notificationId);
    if (notification) {
      notification.read = true;
      this.saveHistory();
    }
  }

  /**
   * Mark all notifications as read
   */
  markAllAsRead(): void {
    this.history.forEach(n => n.read = true);
    this.saveHistory();
  }

  /**
   * Clear notification history
   */
  clearHistory(): void {
    this.history = [];
    this.saveHistory();
  }

  /**
   * Handle localStorage quota exceeded by cleaning up old data
   */
  private handleQuotaExceeded(): void {
    try {
      // Clear old notification history (keep only last 20)
      const historyKey = HISTORY_STORAGE_KEY;
      const savedHistory = localStorage.getItem(historyKey);
      if (savedHistory) {
        const history = JSON.parse(savedHistory);
        if (Array.isArray(history) && history.length > 20) {
          const trimmed = history.slice(0, 20);
          localStorage.setItem(historyKey, JSON.stringify(trimmed));
        }
      }

      // Attempt to clear other non-essential localStorage items
      // In a real app, you'd have a registry of what can be safely cleared
      const keysToKeep = [SETTINGS_STORAGE_KEY, HISTORY_STORAGE_KEY, 'dope-dash-env-config'];
      const allKeys = Object.keys(localStorage);
      for (const key of allKeys) {
        if (!keysToKeep.includes(key)) {
          localStorage.removeItem(key);
        }
      }
    } catch (e) {
      console.error('Error during quota cleanup:', e);
    }
  }

  /**
   * Initialize the service (call after user interaction for audio)
   */
  async initialize(): Promise<void> {
    if (typeof window !== 'undefined') {
      if (this.audioContext && this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      if (this.settings.desktopEnabled && this.notificationPermission === 'default') {
        await this.requestNotificationPermission();
      }
    }
  }
}

// Singleton instance
let notificationServiceInstance: NotificationService | null = null;

export const getNotificationService = (): NotificationService => {
  if (!notificationServiceInstance) {
    notificationServiceInstance = new NotificationService();
  }
  return notificationServiceInstance;
};

export default NotificationService;
