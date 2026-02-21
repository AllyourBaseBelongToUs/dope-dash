"use client";

import { useEffect, useState, useCallback } from "react";
import { X, AlertTriangle, AlertOctagon, AlertCircle, Bell, BellOff, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { QuotaAlert, WebSocketMessage } from "@/types";
import { useEnvironmentStore } from "@/store/environmentStore";
import { getNotificationService } from "@/services/notificationService";

interface AlertBannerProps {
  onAlertClick?: (alert: QuotaAlert) => void;
  onAcknowledge?: (alertId: string) => void;
  maxHeight?: number;
}

const ALERT_TYPE_CONFIG = {
  warning: {
    icon: AlertTriangle,
    bgColor: "bg-yellow-500/10 border-yellow-500/30",
    iconColor: "text-yellow-500",
    badgeVariant: "outline" as const,
    badgeClass: "border-yellow-500 text-yellow-500",
  },
  critical: {
    icon: AlertOctagon,
    bgColor: "bg-orange-500/10 border-orange-500/30",
    iconColor: "text-orange-500",
    badgeVariant: "outline" as const,
    badgeClass: "border-orange-500 text-orange-500",
  },
  overage: {
    icon: AlertCircle,
    bgColor: "bg-red-500/10 border-red-500/30",
    iconColor: "text-red-500",
    badgeVariant: "destructive" as const,
    badgeClass: "",
  },
};

export function AlertBanner({ onAlertClick, onAcknowledge, maxHeight = 300 }: AlertBannerProps) {
  const [alerts, setAlerts] = useState<QuotaAlert[]>([]);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [isMuted, setIsMuted] = useState(false);

  const environmentConfig = useEnvironmentStore((state) => state.config);
  const API_URL = environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch active alerts
  const fetchActiveAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/quota/alerts/active`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.items || []);
      }
    } catch (err) {
      console.error("Failed to fetch active alerts:", err);
    }
  }, [API_URL]);

  // Acknowledge alert
  const acknowledgeAlert = async (alertId: string) => {
    try {
      const res = await fetch(
        `${API_URL}/api/quota/alerts/${alertId}/acknowledge`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ acknowledged_by: "dashboard" }),
        }
      );
      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.id !== alertId));
        onAcknowledge?.(alertId);
      }
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  // Dismiss alert (locally only)
  const dismissAlert = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
  };

  // Handle WebSocket messages for new alerts
  useEffect(() => {
    const handleWebSocketMessage = (event: CustomEvent<WebSocketMessage>) => {
      const message = event.detail;

      if (message.type === "quota_alert") {
        const data = message.data as any;
        const newAlert: QuotaAlert = {
          id: data.id,
          provider_id: data.provider_id,
          provider_name: data.provider_name,
          type: data.alert_type === "overage" ? "exceeded" : data.alert_type,
          alert_type: data.alert_type,
          status: "active",
          metric: "requests",
          threshold: data.threshold_percent,
          threshold_percent: data.threshold_percent,
          current_value: data.current_usage,
          current_usage: data.current_usage,
          quota_limit: data.quota_limit,
          message: data.message,
          created_at: data.timestamp || new Date().toISOString(),
          acknowledged_at: null,
          resolved_at: null,
          updated_at: data.timestamp || new Date().toISOString(),
          metadata: {},
        };

        setAlerts((prev) => {
          // Avoid duplicates
          if (prev.some((a) => a.id === newAlert.id)) {
            return prev;
          }
          return [newAlert, ...prev];
        });

        // Play audio for emergency alerts (95%+)
        if (!isMuted && data.threshold_percent >= 95) {
          const notificationService = getNotificationService();
          notificationService.notify("error", "Quota Emergency", data.message);
        }
      } else if (message.type === "desktop_notification") {
        // Handle desktop notification request from server
        const data = message.data as any;
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification(data.title, {
            body: data.body,
            tag: data.tag,
            requireInteraction: data.requireInteraction,
          });
        }
      } else if (message.type === "audio_alert") {
        // Handle audio alert request from server
        if (!isMuted) {
          const notificationService = getNotificationService();
          notificationService.notify("error", "Quota Emergency", "Quota usage has reached critical level!");
        }
      } else if (message.type === "alert_acknowledged") {
        const data = message.data as any;
        setAlerts((prev) => prev.filter((a) => a.id !== data.alert_id));
      }
    };

    window.addEventListener("ws-message" as any, handleWebSocketMessage);
    return () => {
      window.removeEventListener("ws-message" as any, handleWebSocketMessage);
    };
  }, [isMuted]);

  // Initial fetch
  useEffect(() => {
    fetchActiveAlerts();
    // Poll every 30 seconds
    const interval = setInterval(fetchActiveAlerts, 30000);
    return () => clearInterval(interval);
  }, [fetchActiveAlerts]);

  // Filter out dismissed alerts
  const visibleAlerts = alerts.filter((a) => !dismissedAlerts.has(a.id) && a.status === "active");

  if (visibleAlerts.length === 0) {
    return null;
  }

  return (
    <div
      className="space-y-2 overflow-y-auto"
      style={{ maxHeight: `${maxHeight}px` }}
    >
      {/* Header with mute toggle */}
      <div className="flex items-center justify-between px-2 py-1 bg-muted/50 rounded-md">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">
            {visibleAlerts.length} Active Alert{visibleAlerts.length !== 1 ? "s" : ""}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsMuted(!isMuted)}
          className="h-7 px-2"
        >
          {isMuted ? (
            <BellOff className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Volume2 className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Alert items */}
      {visibleAlerts.map((alert) => {
        const config = ALERT_TYPE_CONFIG[alert.alert_type] || ALERT_TYPE_CONFIG.warning;
        const Icon = config.icon;

        return (
          <Card
            key={alert.id}
            className={cn(
              "border transition-all cursor-pointer hover:shadow-md",
              config.bgColor
            )}
            onClick={() => onAlertClick?.(alert)}
          >
            <div className="p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <Icon className={cn("h-5 w-5 mt-0.5 shrink-0", config.iconColor)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm truncate">
                        {alert.provider_name}
                      </span>
                      <Badge
                        variant={config.badgeVariant}
                        className={cn("text-xs", config.badgeClass)}
                      >
                        {alert.threshold_percent}%
                      </Badge>
                      {alert.is_escalation && (
                        <Badge variant="destructive" className="text-xs">
                          Escalated #{alert.escalation_count}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 truncate">
                      {alert.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(alert.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      acknowledgeAlert(alert.id);
                    }}
                    className="h-7 text-xs"
                  >
                    Acknowledge
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      dismissAlert(alert.id);
                    }}
                    className="h-7 w-7 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
