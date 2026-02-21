"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  RefreshCw,
  List,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Layers,
  Trash2,
  X,
  RotateCcw,
  Calendar,
  AlertCircle,
} from "lucide-react";

interface QueuedRequest {
  id: string;
  provider_id: string;
  project_id: string | null;
  endpoint: string;
  method: string;
  priority: string;
  status: string;
  scheduled_at: string | null;
  retry_count: number;
  max_retries: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  processing_started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  priority_weight: number;
  is_ready: boolean;
  should_retry: boolean;
  wait_time_seconds: number | null;
}

interface QueueStats {
  total_pending: number;
  total_processing: number;
  total_completed: number;
  total_failed: number;
  total_cancelled: number;
  by_priority: Record<string, number>;
  by_provider: Record<string, number>;
  by_project: Record<string, number>;
  oldest_pending: string | null;
  newest_pending: string | null;
  avg_wait_time_seconds: number | null;
  queue_depth: number;
  timestamp: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-yellow-500",
  low: "bg-blue-500",
};

const PRIORITY_BADGES: Record<string, { variant: string; icon: React.ReactNode }> = {
  high: { variant: "destructive", icon: <Zap className="h-3 w-3" /> },
  medium: { variant: "outline", icon: <Layers className="h-3 w-3" /> },
  low: { variant: "secondary", icon: <List className="h-3 w-3" /> },
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-blue-500",
  processing: "bg-yellow-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
  cancelled: "bg-gray-500",
};

interface RequestQueueDashboardProps {
  providerId?: string;
  projectId?: string;
}

export function RequestQueueDashboard({ providerId, projectId }: RequestQueueDashboardProps) {
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [pendingRequests, setPendingRequests] = useState<QueuedRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch queue stats
  const fetchQueueStats = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (providerId) params.append("provider_id", providerId);
      if (projectId) params.append("project_id", projectId);

      const response = await fetch(`${API_URL}/api/queue/stats?${params}`);
      if (!response.ok) throw new Error("Failed to fetch queue stats");

      const data = await response.json();
      setQueueStats(data);
    } catch (err) {
      console.error("Error fetching queue stats:", err);
    }
  }, [API_URL, providerId, projectId]);

  // Fetch pending requests
  const fetchPendingRequests = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (providerId) params.append("provider_id", providerId);
      if (projectId) params.append("project_id", projectId);
      params.append("limit", "50");

      const response = await fetch(`${API_URL}/api/queue/pending?${params}`);
      if (!response.ok) throw new Error("Failed to fetch pending requests");

      const data = await response.json();
      setPendingRequests(data.items || []);
    } catch (err) {
      console.error("Error fetching pending requests:", err);
    }
  }, [API_URL, providerId, projectId]);

  // Combined fetch
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([fetchQueueStats(), fetchPendingRequests()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [fetchQueueStats, fetchPendingRequests]);

  // Cancel request
  const cancelRequest = async (requestId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/queue/requests/${requestId}/cancel`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to cancel request");

      await fetchData();
    } catch (err) {
      console.error("Error cancelling request:", err);
    }
  };

  // Retry failed request
  const retryRequest = async (requestId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/queue/requests/${requestId}/retry`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to retry request");

      await fetchData();
    } catch (err) {
      console.error("Error retrying request:", err);
    }
  };

  // Delete request
  const deleteRequest = async (requestId: string) => {
    if (!confirm("Are you sure you want to delete this request?")) return;

    try {
      const response = await fetch(`${API_URL}/api/queue/requests/${requestId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete request");

      await fetchData();
    } catch (err) {
      console.error("Error deleting request:", err);
    }
  };

  // Flush old completed/failed requests
  const flushOldRequests = async () => {
    if (!confirm("Delete completed, failed, and cancelled requests older than 7 days?")) return;

    try {
      const response = await fetch(`${API_URL}/api/queue/flush`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          older_than: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        }),
      });
      if (!response.ok) throw new Error("Failed to flush queue");

      await fetchData();
    } catch (err) {
      console.error("Error flushing queue:", err);
    }
  };

  // Format duration
  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "Now";
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins < 60) return `${mins}m ${secs}s`;
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return `${hours}h ${remainingMins}m`;
  };

  // Format date
  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  // Get status badge
  const getStatusBadge = (request: QueuedRequest) => {
    const status = request.status;
    if (status === "failed") {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    }
    if (status === "completed") {
      return (
        <Badge variant="outline" className="gap-1 border-green-500 text-green-500">
          <CheckCircle className="h-3 w-3" />
          Completed
        </Badge>
      );
    }
    if (status === "processing") {
      return (
        <Badge variant="outline" className="gap-1 border-yellow-500 text-yellow-500">
          <RefreshCw className="h-3 w-3" />
          Processing
        </Badge>
      );
    }
    if (status === "cancelled") {
      return (
        <Badge variant="secondary" className="gap-1">
          <X className="h-3 w-3" />
          Cancelled
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="gap-1 border-blue-500 text-blue-500">
        <Clock className="h-3 w-3" />
        Pending
      </Badge>
    );
  };

  // Get priority badge
  const getPriorityBadge = (priority: string) => {
    const config = PRIORITY_BADGES[priority] || PRIORITY_BADGES.medium;
    return (
      <Badge variant={config.variant as any} className="gap-1">
        {config.icon}
        {priority.charAt(0).toUpperCase() + priority.slice(1)}
      </Badge>
    );
  };

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading && !queueStats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Request Queue</CardTitle>
          <CardDescription>Loading queue data...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-40">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <List className="h-6 w-6 text-blue-500" />
            Request Queue
          </h2>
          <p className="text-muted-foreground">
            Priority-based request throttling and queue management
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={flushOldRequests}
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" />
            Flush Old
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Queue Stats */}
      {queueStats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Pending</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-500">
                {queueStats.total_pending}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Processing</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-500">
                {queueStats.total_processing}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completed</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">
                {queueStats.total_completed}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Failed</CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${
                  queueStats.total_failed > 0 ? "text-red-500" : ""
                }`}
              >
                {queueStats.total_failed}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Queue Depth Indicator */}
      {queueStats && queueStats.queue_depth > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Queue Depth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Current Queue Load</span>
                <span className="font-medium">{queueStats.queue_depth} requests</span>
              </div>
              <Progress
                value={Math.min(100, (queueStats.queue_depth / 50) * 100)}
                className="h-2"
              />
              {queueStats.avg_wait_time_seconds && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>Average wait: {formatDuration(queueStats.avg_wait_time_seconds)}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Priority Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Queue Priority Levels</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              {getPriorityBadge("high")}
              <span className="text-muted-foreground">Critical requests</span>
            </div>
            <div className="flex items-center gap-2">
              {getPriorityBadge("medium")}
              <span className="text-muted-foreground">Standard requests</span>
            </div>
            <div className="flex items-center gap-2">
              {getPriorityBadge("low")}
              <span className="text-muted-foreground">Background tasks</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pending Requests */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Requests</CardTitle>
          <CardDescription>
            {pendingRequests.length === 0
              ? "No pending requests in queue"
              : `${pendingRequests.length} request(s) waiting to process`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pendingRequests.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
              <p>Queue is empty</p>
              <p className="text-sm">All requests have been processed</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pendingRequests.map((request) => (
                <div
                  key={request.id}
                  className="flex items-start justify-between p-4 rounded-lg hover:bg-muted/50 transition-colors border"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {getPriorityBadge(request.priority)}
                      <span className="text-sm font-medium">
                        {request.method} {request.endpoint}
                      </span>
                      {request.wait_time_seconds !== null && request.wait_time_seconds > 0 && (
                        <Badge variant="outline" className="gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDuration(request.wait_time_seconds)}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>Queued {formatDate(request.created_at)}</span>
                      {request.retry_count > 0 && (
                        <span className="text-orange-500">
                          Retry {request.retry_count}/{request.max_retries}
                        </span>
                      )}
                      {request.last_error && (
                        <span className="text-red-500 truncate max-w-xs" title={request.last_error}>
                          Error: {request.last_error}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelRequest(request.id)}
                      className="h-8 w-8 p-0"
                      title="Cancel request"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Priority Distribution */}
      {queueStats && queueStats.by_priority && Object.keys(queueStats.by_priority).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Priority Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(queueStats.by_priority)
                .sort(([, a], [, b]) => b - a)
                .map(([priority, count]) => (
                  <div key={priority} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        {getPriorityBadge(priority)}
                        <span className="capitalize">{priority}</span>
                      </span>
                      <span className="font-medium">{count} requests</span>
                    </div>
                    <Progress
                      value={queueStats.total_pending > 0 ? (count / queueStats.total_pending) * 100 : 0}
                      className="h-2"
                    />
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
