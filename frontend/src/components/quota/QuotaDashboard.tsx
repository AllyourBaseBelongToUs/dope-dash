"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock } from "lucide-react";
import type { QuotaUsage, QuotaAlert, QuotaSummary, Provider, WebSocketMessage } from "@/types";
import { useEnvironmentStore } from "@/store/environmentStore";

const PROVIDER_COLORS: Record<string, string> = {
  claude: "bg-orange-500",
  gemini: "bg-blue-500",
  openai: "bg-green-500",
  cursor: "bg-purple-500",
};

const PROVIDER_GRADIENTS: Record<string, string> = {
  claude: "from-orange-500 to-orange-600",
  gemini: "from-blue-500 to-blue-600",
  openai: "from-green-500 to-green-600",
  cursor: "from-purple-500 to-purple-600",
};

interface QuotaData {
  providers: Provider[];
  usages: QuotaUsage[];
  alerts: QuotaAlert[];
  summary: QuotaSummary | null;
}

export function QuotaDashboard() {
  const [quotaData, setQuotaData] = useState<QuotaData>({
    providers: [],
    usages: [],
    alerts: [],
    summary: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const environmentConfig = useEnvironmentStore((state) => state.config);
  // Core API on 8000, WebSocket on 8005 (step-5 spacing)
  const API_URL = environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const WS_URL = environmentConfig?.wsUrl || process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8005/ws";

  // Fetch quota data
  const fetchQuotaData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [providersRes, usagesRes, alertsRes, summaryRes] = await Promise.all([
        fetch(`${API_URL}/api/quota/providers`),
        fetch(`${API_URL}/api/quota/usage`),
        fetch(`${API_URL}/api/quota/alerts`),
        fetch(`${API_URL}/api/quota/summary`),
      ]);

      if (!providersRes.ok || !usagesRes.ok || !alertsRes.ok || !summaryRes.ok) {
        throw new Error("Failed to fetch quota data");
      }

      const [providers, usages, alerts, summary] = await Promise.all([
        providersRes.json(),
        usagesRes.json(),
        alertsRes.json(),
        summaryRes.json(),
      ]);

      setQuotaData({
        providers: providers.items || [],
        usages: usages.items || [],
        alerts: alerts.items || [],
        summary: summary,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  // Acknowledge alert
  const acknowledgeAlert = async (alertId: string) => {
    try {
      const res = await fetch(
        `${API_URL}/api/quota/alerts/${alertId}/acknowledge`,
        { method: "POST" }
      );
      if (res.ok) {
        fetchQuotaData();
      }
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  // Handle WebSocket messages for quota updates
  // We listen for global WebSocket messages through a custom event
  useEffect(() => {
    const handleWebSocketMessage = (event: CustomEvent<WebSocketMessage>) => {
      const message = event.detail;

      if (message.type === "quota_update") {
        const data = message.data as any;
        setQuotaData((prev) => ({
          ...prev,
          usages: prev.usages.map((u) =>
            u.provider_id === data.provider_id &&
            (u.project_id === data.project_id ||
             (u.project_id === null && data.project_id === null))
              ? {
                  ...u,
                  current_requests: data.current_requests,
                  current_tokens: data.current_tokens,
                  usage_percent: data.usage_percent,
                  is_over_limit: data.is_over_limit,
                  remaining_requests: data.remaining_requests,
                }
              : u
          ),
        }));
      } else if (message.type === "quota_alert") {
        const data = message.data as any;
        setQuotaData((prev) => ({
          ...prev,
          alerts: [
            {
              ...data,
              acknowledged_at: null,
              resolved_at: null,
              created_at: data.timestamp,
              updated_at: data.timestamp,
              metadata: {},
            },
            ...prev.alerts,
          ],
        }));
        fetchQuotaData(); // Full refresh to get all data
      }
    };

    // Listen for WebSocket messages dispatched globally
    window.addEventListener("ws-message" as any, handleWebSocketMessage);
    return () => {
      window.removeEventListener("ws-message" as any, handleWebSocketMessage);
    };
  }, [fetchQuotaData]);

  // Initial fetch
  useEffect(() => {
    fetchQuotaData();
    const interval = setInterval(fetchQuotaData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchQuotaData]);

  // Get quota usage for a provider
  const getUsageForProvider = (providerId: string) => {
    return quotaData.usages.find((u) => u.provider_id === providerId && u.project_id === null);
  };

  // Format time until reset
  const formatTimeUntilReset = (seconds: number | null) => {
    if (!seconds) return "Unknown";
    if (seconds <= 0) "Due now";
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    return `${hours}h ${mins}m`;
  };

  // Get status badge
  const getStatusBadge = (usage: QuotaUsage) => {
    if (usage.is_over_limit) {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Over Limit
        </Badge>
      );
    }
    if (usage.usage_percent >= 95) {
      return (
        <Badge variant="destructive" className="gap-1">
          <AlertTriangle className="h-3 w-3" />
          Critical
        </Badge>
      );
    }
    if (usage.usage_percent >= 80) {
      return (
        <Badge variant="outline" className="gap-1 border-yellow-500 text-yellow-500">
          <AlertTriangle className="h-3 w-3" />
          Warning
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="gap-1 border-green-500 text-green-500">
        <CheckCircle className="h-3 w-3" />
        OK
      </Badge>
    );
  };

  if (loading && quotaData.providers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API Quota Tracking</CardTitle>
          <CardDescription>Loading quota data...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-40">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && quotaData.providers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API Quota Tracking</CardTitle>
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

  const activeAlerts = quotaData.alerts.filter((a) => a.status === "active");

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">API Quota Tracking</h2>
          <p className="text-muted-foreground">
            Real-time monitoring of API provider usage and limits
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchQuotaData}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      {quotaData.summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Usage</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {quotaData.summary.total_usage_percent}%
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Alerts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${activeAlerts.length > 0 ? "text-red-500" : ""}`}>
                {activeAlerts.length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Critical Alerts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${quotaData.summary.alerts_critical > 0 ? "text-red-500" : ""}`}>
                {quotaData.summary.alerts_critical}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Over Limit</CardDescription>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${quotaData.summary.providers_over_limit > 0 ? "text-red-500" : ""}`}>
                {quotaData.summary.providers_over_limit}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <Card className="border-red-500/50 bg-red-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Active Alerts ({activeAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start justify-between p-3 rounded-lg bg-background/50 border"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant={
                          alert.alert_type === "critical" || alert.alert_type === "overage"
                            ? "destructive"
                            : "outline"
                        }
                      >
                        {alert.alert_type}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {alert.threshold_percent}% used
                      </span>
                    </div>
                    <p className="text-sm">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {alert.current_usage} / {alert.quota_limit} requests
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => acknowledgeAlert(alert.id)}
                  >
                    Acknowledge
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Provider Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {quotaData.providers.map((provider) => {
          const usage = getUsageForProvider(provider.id);
          const color = PROVIDER_COLORS[provider.name] || "bg-gray-500";
          const gradient = PROVIDER_GRADIENTS[provider.name] || "from-gray-500 to-gray-600";

          return (
            <Card key={provider.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="capitalize">{provider.display_name}</CardTitle>
                  {usage ? getStatusBadge(usage) : <Badge variant="outline">No Data</Badge>}
                </div>
                <CardDescription>
                  {provider.api_endpoint || "No endpoint configured"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {usage ? (
                  <div className="space-y-4">
                    {/* Usage Progress */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">Request Usage</span>
                        <span className={`text-sm font-bold ${
                          usage.is_over_limit ? "text-red-500" :
                          usage.usage_percent >= 80 ? "text-yellow-500" :
                          "text-green-500"
                        }`}>
                          {usage.current_requests.toLocaleString()} / {usage.quota_limit.toLocaleString()}
                        </span>
                      </div>
                      <Progress
                        value={Math.min(usage.usage_percent, 100)}
                        className="h-3"
                      />
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">
                          {usage.usage_percent.toFixed(1)}% used
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {usage.remaining_requests.toLocaleString()} remaining
                        </span>
                      </div>
                    </div>

                    {/* Token Usage (if available) */}
                    {usage.quota_limit_tokens && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">Token Usage</span>
                          <span className="text-sm text-muted-foreground">
                            {usage.current_tokens.toLocaleString()} / {usage.quota_limit_tokens.toLocaleString()}
                          </span>
                        </div>
                        <Progress
                          value={(usage.current_tokens / usage.quota_limit_tokens) * 100}
                          className="h-2"
                        />
                      </div>
                    )}

                    {/* Reset Info */}
                    <div className="flex items-center justify-between pt-2 border-t">
                      {usage.time_until_reset_seconds != null && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          <span>Resets in: {formatTimeUntilReset(usage.time_until_reset_seconds ?? null)}</span>
                        </div>
                      )}
                      {usage.overage_count && usage.overage_count > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          {usage.overage_count} overages
                        </Badge>
                      )}
                    </div>

                    {/* Rate Limits Info */}
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t text-xs text-muted-foreground">
                      {provider.rate_limit_rpm && (
                        <div>{provider.rate_limit_rpm} req/min</div>
                      )}
                      {provider.rate_limit_tpm && (
                        <div>{provider.rate_limit_tpm.toLocaleString()} tokens/min</div>
                      )}
                      {provider.rate_limit_tokens_per_day && (
                        <div>{provider.rate_limit_tokens_per_day.toLocaleString()} tokens/day</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No usage data available
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* No providers message */}
      {quotaData.providers.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No providers configured</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
