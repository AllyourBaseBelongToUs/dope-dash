'use client';

import { Bell, CheckCircle2, XCircle, StopCircle, Clock, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNotificationStore } from '@/store/notificationStore';
import { useEffect, useState } from 'react';
import type { Notification } from '@/types';

const notificationIcons = {
  spec_complete: CheckCircle2,
  error: XCircle,
  agent_stopped: StopCircle,
};

const notificationColors = {
  spec_complete: 'text-green-500',
  error: 'text-red-500',
  agent_stopped: 'text-yellow-500',
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

interface NotificationHistoryProps {
  className?: string;
}

export function NotificationHistory({ className }: NotificationHistoryProps) {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearNotifications } = useNotificationStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Notifications</h2>
          {unreadCount > 0 && (
            <span className="h-5 px-2 rounded-full bg-primary text-primary-foreground text-xs font-medium flex items-center">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={markAllAsRead}>
              Mark all read
            </Button>
          )}
          {notifications.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearNotifications}>
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No notifications yet</p>
          </div>
        ) : (
          notifications.map((notification) => {
            const Icon = notificationIcons[notification.type];
            const colorClass = notificationColors[notification.type];

            return (
              <div
                key={notification.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent ${
                  !notification.read ? 'bg-accent/50 border-primary/50' : 'bg-background'
                }`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${colorClass}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="font-medium text-sm truncate">{notification.title}</h4>
                      <span className="text-xs text-muted-foreground flex items-center gap-1 flex-shrink-0">
                        <Clock className="h-3 w-3" />
                        {formatTimestamp(notification.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{notification.message}</p>
                    {notification.sessionId && (
                      <p className="text-xs text-muted-foreground mt-1 font-mono">
                        Session: {notification.sessionId.slice(0, 8)}...
                      </p>
                    )}
                  </div>
                  {!notification.read && (
                    <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-2" />
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
