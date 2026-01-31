'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Trash2,
  RefreshCw,
  Clock,
  AlertTriangle,
  CheckCircle,
  Calendar,
  Database,
  Bell,
  Settings,
} from 'lucide-react';

interface RetentionSummary {
  events: {
    total: number;
    to_delete: number;
    upcoming_expiration: number;
    retention_days: number;
    cutoff_date: string;
    oldest_date: string | null;
  };
  sessions: {
    total: number;
    to_delete: number;
    upcoming_expiration: number;
    retention_days: number;
    cutoff_date: string;
    oldest_date: string | null;
  };
  warnings: Array<{
    type: string;
    message: string;
    severity: string;
    count: number;
  }>;
  generated_at: string;
}

interface CleanupResult {
  dry_run: boolean;
  events: {
    deleted_count: number;
    soft_deleted_count: number;
    permanently_deleted_count: number;
    total_deleted_count: number;
  };
  sessions: {
    deleted_count: number;
    soft_deleted_count: number;
    permanently_deleted_count: number;
    total_deleted_count: number;
  };
  total_deleted: number;
  total_duration_seconds: number;
  completed_at: string;
}

interface Notification {
  id: string;
  type: string;
  severity: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
  read: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Retention Dashboard Component
 *
 * Displays data retention status, warnings, and allows manual cleanup triggers.
 */
export function RetentionDashboard() {
  const [summary, setSummary] = useState<RetentionSummary | null>(null);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [dryRun, setDryRun] = useState(true);

  const fetchSummary = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/retention/summary`);
      if (!response.ok) throw new Error('Failed to fetch retention summary');
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error fetching retention summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/retention/notifications`);
      if (!response.ok) throw new Error('Failed to fetch notifications');
      const data = await response.json();
      setNotifications(data.notifications || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const runCleanup = async () => {
    setCleanupLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/retention/cleanup?dry_run=${dryRun}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to run cleanup');
      const data = await response.json();
      setCleanupResult(data);
      // Refresh summary and notifications after cleanup
      await fetchSummary();
      await fetchNotifications();
    } catch (error) {
      console.error('Error running cleanup:', error);
    } finally {
      setCleanupLoading(false);
    }
  };

  const markAsRead = async (notificationId: string) => {
    try {
      await fetch(`${API_BASE}/api/retention/notifications/${notificationId}/read`, {
        method: 'POST',
      });
      await fetchNotifications();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const clearOldNotifications = async () => {
    try {
      await fetch(`${API_BASE}/api/retention/notifications?older_than_hours=24`, {
        method: 'DELETE',
      });
      await fetchNotifications();
    } catch (error) {
      console.error('Error clearing notifications:', error);
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchNotifications();
    // Refresh every 5 minutes
    const interval = setInterval(() => {
      fetchSummary();
      fetchNotifications();
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'destructive';
      case 'warning':
        return 'secondary';
      case 'success':
        return 'default';
      default:
        return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Data Retention</h2>
          <p className="text-sm text-muted-foreground">
            Manage data lifecycle and cleanup policies
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchSummary}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="default" size="sm">
                <Trash2 className="mr-2 h-4 w-4" />
                Run Cleanup
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Confirm Data Cleanup</AlertDialogTitle>
                <AlertDialogDescription>
                  This will {dryRun ? 'preview' : 'permanently'} delete data that exceeds
                  the retention period. {dryRun && 'No data will be deleted in dry run mode.'}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="flex items-center gap-2 py-4">
                <input
                  type="checkbox"
                  id="dry-run"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  className="h-4 w-4"
                />
                <label htmlFor="dry-run" className="text-sm">
                  Dry run (preview only, no actual deletion)
                </label>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={runCleanup} disabled={cleanupLoading}>
                  {cleanupLoading ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>Run Cleanup</>
                  )}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Retention Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Events Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Events
            </CardTitle>
            <CardDescription>
              {formatNumber(summary?.events.total || 0)} total events
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Retention Period</span>
              <Badge variant="outline">
                <Clock className="mr-1 h-3 w-3" />
                {summary?.events.retention_days} days
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">To Delete</span>
              <Badge variant={summary?.events.to_delete ? 'destructive' : 'default'}>
                {formatNumber(summary?.events.to_delete || 0)}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Expiring Soon</span>
              <Badge variant={summary?.events.upcoming_expiration ? 'secondary' : 'default'}>
                {formatNumber(summary?.events.upcoming_expiration || 0)}
              </Badge>
            </div>
            <div className="text-xs text-muted-foreground">
              Oldest: {summary?.events.oldest_date
                ? formatDate(summary.events.oldest_date)
                : 'N/A'}
            </div>
          </CardContent>
        </Card>

        {/* Sessions Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Sessions
            </CardTitle>
            <CardDescription>
              {formatNumber(summary?.sessions.total || 0)} total sessions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Retention Period</span>
              <Badge variant="outline">
                <Clock className="mr-1 h-3 w-3" />
                {summary?.sessions.retention_days} days
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">To Delete</span>
              <Badge variant={summary?.sessions.to_delete ? 'destructive' : 'default'}>
                {formatNumber(summary?.sessions.to_delete || 0)}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Expiring Soon</span>
              <Badge variant={summary?.sessions.upcoming_expiration ? 'secondary' : 'default'}>
                {formatNumber(summary?.sessions.upcoming_expiration || 0)}
              </Badge>
            </div>
            <div className="text-xs text-muted-foreground">
              Oldest: {summary?.sessions.oldest_date
                ? formatDate(summary.sessions.oldest_date)
                : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Warnings */}
      {summary?.warnings && summary.warnings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-warning" />
              Warnings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {summary.warnings.map((warning, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg border bg-background"
                >
                  <Badge variant={getSeverityColor(warning.severity) as any}>
                    {warning.severity}
                  </Badge>
                  <span className="text-sm">{warning.message}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cleanup Result */}
      {cleanupResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-success" />
              Cleanup {cleanupResult.dry_run ? 'Preview' : 'Result'}
            </CardTitle>
            <CardDescription>
              {cleanupResult.dry_run
                ? 'This was a dry run - no data was actually deleted'
                : `Completed in ${cleanupResult.total_duration_seconds.toFixed(2)}s`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium mb-2">Events</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Soft deleted:</span>
                      <span>{formatNumber(cleanupResult.events.soft_deleted_count)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Permanently deleted:</span>
                      <span>{formatNumber(cleanupResult.events.permanently_deleted_count)}</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-2">Sessions</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Soft deleted:</span>
                      <span>{formatNumber(cleanupResult.sessions.soft_deleted_count)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Permanently deleted:</span>
                      <span>{formatNumber(cleanupResult.sessions.permanently_deleted_count)}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="pt-4 border-t">
                <div className="flex justify-between">
                  <span className="font-medium">Total Deleted:</span>
                  <span className="font-bold">{formatNumber(cleanupResult.total_deleted)}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            {notifications.filter((n) => !n.read).length} unread
          </CardDescription>
        </CardHeader>
        <CardContent>
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground">No notifications</p>
          ) : (
            <div className="space-y-2">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${
                    notification.read ? 'bg-muted/50' : 'bg-background'
                  }`}
                >
                  <Badge variant={getSeverityColor(notification.severity) as any}>
                    {notification.severity}
                  </Badge>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{notification.title}</p>
                    <p className="text-xs text-muted-foreground">{notification.message}</p>
                  </div>
                  {!notification.read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markAsRead(notification.id)}
                    >
                      Mark Read
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
          {notifications.length > 0 && (
            <div className="mt-4">
              <Button variant="outline" size="sm" onClick={clearOldNotifications}>
                Clear Old Notifications
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
