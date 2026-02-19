"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  RotateCcw,
  Zap,
  Activity,
} from "lucide-react";
import type {
  RateLimitEvent,
  RateLimitEventSummary,
  Provider,
  WebSocketMessage,
} from "@/types";
import { useEnvironmentStore } from "@/store/environmentStore";

const STATUS_COLORS: Record<string, string> = {
  detected: "bg-orange-500",
  retrying: "bg-yellow-500",
  resolved: "bg-green-500",
  failed: "bg-red-500",
};

const STATUS_GRADIENTS: Record<string, string> = {
  detected: "from-orange-500 to-orange-600",
  retrying: "from-yellow-500 to-yellow-600",
  resolved: "from-green-500 to-green-600",
  failed: "from-red-500 to-red-600",
};

interface RateLimitData {
  events: RateLimitEvent[];
  summary: RateLimitEventSummary | null;
  providers: Provider[];
}

export function RateLimitDashboard() {
  const [rateLimitData, setRateLimitData] = useState<RateLimitData>({
    events: [],
    summary: null,
    providers: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const environmentConfig = useEnvironmentStore((state) => state.config);
  const API_URL =
    environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch rate limit data
  const fetchRateLimitData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [eventsRes, summaryRes, providersRes] = await Promise.all([
        fetch(`${API_URL}/api/rate-limit/events?limit=50`),
        fetch(`${API_URL}/api/rate-limit/events/summary`),
        fetch(`${API_URL}/api/quota/providers`),
      ]);

      if (!eventsRes.ok || !summaryRes.ok || !providersRes.ok) {
        throw new Error("Failed to fetch rate limit data");
      }

      const [eventsData, summaryData, providersData] = await Promise.all([
        eventsRes.json(),
        summaryRes.json(),
        providersRes.json(),
      ]);

      setRateLimitData({
        events: eventsData.items || [],
        summary: summaryData,
        providers: providersData.items || [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  // Format duration
  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "Unknown";
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
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

  // Get provider name by ID
  const getProviderName = (providerId: string) => {
    const provider = rateLimitData.providers.find((p) => p.id === providerId);
    return provider?.display_name || providerId;
  };

  // Get status badge
  const getStatusBadge = (event: RateLimitEvent) => {
    const status = event.status;
    if (status === "failed") {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    }
    if (status === "resolved") {
      return (
        <Badge variant="outline" className="gap-1 border-green-500 text-green-500">
          <CheckCircle className="h-3 w-3" />
          Resolved
        </Badge>
      );
    }
    if (status === "retrying") {
      return (
        <Badge variant="outline" className="gap-1 border-yellow-500 text-yellow-500">
          <RotateCcw className="h-3 w-3" />
          Retrying ({event.attempt_number}/{event.max_attempts})
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="gap-1 border-orange-500 text-orange-500">
        <AlertTriangle className="h-3 w-3" />
        Detected
      </Badge>
    );
  };

  // Calculate backoff for next attempt
  const getBackoffInfo = (event: RateLimitEvent) => {
    if (event.status !== "detected" && event.status !== "retrying") {
      return null;
    }
    const base = event.calculated_backoff_seconds || 2 ** (event.attempt_number - 1);
    const jitter = event.jitter_seconds || 0;
    return {
      base,
      jitter,
      total: base + jitter,
    };
  };

  // Handle WebSocket messages for rate limit updates
  useEffect(() => {
    const handleWebSocketMessage = (event: CustomEvent<WebSocketMessage>) => {
      const message = event.detail;

      if (
        message.type === "rate_limit_detected" ||
        message.type === "rate_limit_resolved" ||
        message.type === "rate_limit_failed"
      ) {
        // Refresh data on rate limit events
        fetchRateLimitData();
      }
    };

    window.addEventListener("ws-message" as any, handleWebSocketMessage);
    return () => {
      window.removeEventListener("ws-message" as any, handleWebSocketMessage);
    };
  }, [fetchRateLimitData]);

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchRateLimitData();
    const interval = setInterval(fetchRateLimitData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchRateLimitData]);

  if (loading && rateLimitData.events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Rate Limit Detection</CardTitle>
          <CardDescription>Loading rate limit events...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-40">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && rateLimitData.events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Rate Limit Detection</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-red-500 py-8">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
            <p>{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const activeEvents = rateLimitData.events.filter(
    (e) => e.status === "detected" || e.status === "retrying"
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-yellow-500" />
            Rate Limit Detection
          </h2>
          <p className="text-muted-foreground">
            429 error tracking with exponential backoff retry
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchRateLimitData}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      {rateLimitData.summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Events</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{rateLimitData.summary.total_events}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Events</CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${
                  activeEvents.length > 0 ? "text-orange-500" : ""
                }`}
              >
                {activeEvents.length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Resolved</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">
                {rateLimitData.summary.resolved_events}
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
                  rateLimitData.summary.failed_events > 0 ? "text-red-500" : ""
                }`}
              >
                {rateLimitData.summary.failed_events}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Backoff Pattern Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Exponential Backoff Pattern</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant="outline">1</Badge>
              <span className="text-muted-foreground">→ 1s delay</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">2</Badge>
              <span className="text-muted-foreground">→ 2s delay</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">3</Badge>
              <span className="text-muted-foreground">→ 4s delay</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">4</Badge>
              <span className="text-muted-foreground">→ 8s delay</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">5</Badge>
              <span className="text-muted-foreground">→ 16s delay</span>
            </div>
            <div className="ml-auto text-xs text-muted-foreground">
              + jitter to prevent thundering herd
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Events Alert */}
      {activeEvents.length > 0 && (
        <Card className="border-orange-500/50 bg-orange-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-orange-500" />
              Active Rate Limit Events ({activeEvents.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeEvents.map((event) => {
                const backoff = getBackoffInfo(event);
                return (
                  <div
                    key={event.id}
                    className="p-4 rounded-lg bg-background/50 border space-y-2"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {getStatusBadge(event)}
                          <span className="text-sm font-medium">
                            {getProviderName(event.provider_id)}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            HTTP {event.http_status_code}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground font-mono truncate">
                          {event.request_method} {event.request_endpoint}
                        </p>
                      </div>
                      {backoff && (
                        <div className="text-right">
                          <div className="text-xs text-muted-foreground">Next retry in</div>
                          <div className="text-lg font-bold text-orange-500">
                            {formatDuration(backoff.total)}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Retry Progress */}
                    {event.max_attempts > 1 && (
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-muted-foreground">
                            Retry Progress
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {event.attempt_number} / {event.max_attempts}
                          </span>
                        </div>
                        <Progress
                          value={(event.attempt_number / event.max_attempts) * 100}
                          className="h-2"
                        />
                      </div>
                    )}

                    {/* Retry-After Info */}
                    {event.retry_after_seconds && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>
                          Retry-After header: {event.retry_after_seconds}s
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
          <CardDescription>History of rate limit detection and retries</CardDescription>
        </CardHeader>
        <CardContent>
          {rateLimitData.events.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
              <p>No rate limit events detected</p>
              <p className="text-sm">API requests are flowing smoothly</p>
            </div>
          ) : (
            <div className="space-y-2">
              {rateLimitData.events.map((event) => {
                const backoff = getBackoffInfo(event);
                return (
                  <div
                    key={event.id}
                    className="flex items-start justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors border"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(event)}
                        <span className="text-sm font-medium">
                          {getProviderName(event.provider_id)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(event.detected_at)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground font-mono truncate">
                        {event.request_method} {event.request_endpoint}
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                        <span>Attempt {event.attempt_number}/{event.max_attempts}</span>
                        {event.retry_after_seconds && (
                          <span>Retry-After: {event.retry_after_seconds}s</span>
                        )}
                        {event.resolved_at && (
                          <span className="text-green-500">
                            Resolved after {event.attempt_number} attempts
                          </span>
                        )}
                        {event.failed_at && (
                          <span className="text-red-500">Failed after max retries</span>
                        )}
                      </div>
                    </div>
                    {backoff && (
                      <div className="text-right ml-4">
                        <div className="text-xs text-muted-foreground">Next retry</div>
                        <div className="text-sm font-bold text-orange-500">
                          {formatDuration(backoff.total)}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
