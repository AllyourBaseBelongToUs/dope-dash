"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "@/components/ui/alert-dialog";
import {
  AlertTriangle,
  AlertOctagon,
  AlertCircle,
  CheckCircle,
  Clock,
  Filter,
  RefreshCw,
  Check,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { QuotaAlert } from "@/types";
import { useEnvironmentStore } from "@/store/environmentStore";

interface AlertHistoryProps {
  providerId?: string;
  limit?: number;
  showFilters?: boolean;
}

const ALERT_TYPE_CONFIG = {
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    label: "Warning",
    bgColor: "bg-yellow-500/10",
  },
  critical: {
    icon: AlertOctagon,
    color: "text-orange-500",
    label: "Critical",
    bgColor: "bg-orange-500/10",
  },
  overage: {
    icon: AlertCircle,
    color: "text-red-500",
    label: "Emergency",
    bgColor: "bg-red-500/10",
  },
};

const STATUS_CONFIG = {
  active: {
    label: "Active",
    variant: "destructive" as const,
    icon: AlertCircle,
  },
  acknowledged: {
    label: "Acknowledged",
    variant: "secondary" as const,
    icon: Check,
  },
  resolved: {
    label: "Resolved",
    variant: "outline" as const,
    icon: CheckCircle,
  },
};

export function AlertHistory({ providerId, limit = 50, showFilters = true }: AlertHistoryProps) {
  const [alerts, setAlerts] = useState<QuotaAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const environmentConfig = useEnvironmentStore((state) => state.config);
  const API_URL = environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch alert history
  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);

      const params = new URLSearchParams();
      params.set("limit", limit.toString());

      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      if (typeFilter !== "all") {
        params.set("alert_type", typeFilter);
      }
      if (providerId) {
        params.set("provider_id", providerId);
      }

      const res = await fetch(`${API_URL}/api/quota/alerts/history?${params}`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.items || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error("Failed to fetch alert history:", err);
    } finally {
      setLoading(false);
    }
  }, [API_URL, limit, statusFilter, typeFilter, providerId]);

  // Acknowledge single alert
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
        fetchAlerts();
      }
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  // Resolve single alert
  const resolveAlert = async (alertId: string) => {
    try {
      const res = await fetch(
        `${API_URL}/api/quota/alerts/${alertId}/resolve`,
        { method: "POST" }
      );
      if (res.ok) {
        fetchAlerts();
      }
    } catch (err) {
      console.error("Failed to resolve alert:", err);
    }
  };

  // Bulk acknowledge
  const bulkAcknowledge = async () => {
    if (selectedAlerts.size === 0) return;

    try {
      const res = await fetch(`${API_URL}/api/quota/alerts/bulk/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alert_ids: Array.from(selectedAlerts),
          acknowledged_by: "dashboard",
        }),
      });
      if (res.ok) {
        setSelectedAlerts(new Set());
        fetchAlerts();
      }
    } catch (err) {
      console.error("Failed to bulk acknowledge:", err);
    }
  };

  // Toggle alert selection
  const toggleAlertSelection = (alertId: string) => {
    setSelectedAlerts((prev) => {
      const next = new Set(prev);
      if (next.has(alertId)) {
        next.delete(alertId);
      } else {
        next.add(alertId);
      }
      return next;
    });
  };

  // Select/deselect all visible active alerts
  const toggleSelectAll = () => {
    const activeAlertIds = alerts
      .filter((a) => a.status === "active")
      .map((a) => a.id);

    if (selectedAlerts.size === activeAlertIds.length) {
      setSelectedAlerts(new Set());
    } else {
      setSelectedAlerts(new Set(activeAlertIds));
    }
  };

  // Initial fetch and filter changes
  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const activeAlertsCount = alerts.filter((a) => a.status === "active").length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              Alert History
              {activeAlertsCount > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {activeAlertsCount} Active
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {total} total alerts
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {selectedAlerts.size > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    Acknowledge {selectedAlerts.size} Selected
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Bulk Acknowledge Alerts</AlertDialogTitle>
                    <AlertDialogDescription>
                      Are you sure you want to acknowledge {selectedAlerts.size} selected alerts?
                      This will stop escalation for these alerts.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={bulkAcknowledge}>
                      Acknowledge
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}

            <Button variant="outline" size="sm" onClick={fetchAlerts}>
              <RefreshCw className={cn("h-4 w-4 mr-1", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        {showFilters && (
          <div className="flex items-center gap-4 pt-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Filters:</span>
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="acknowledged">Acknowledged</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>

            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="warning">Warning (80%)</SelectItem>
                <SelectItem value="critical">Critical (90%)</SelectItem>
                <SelectItem value="overage">Emergency (95%+)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
      </CardHeader>

      <CardContent>
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No alerts found</p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <input
                      type="checkbox"
                      checked={
                        alerts.filter((a) => a.status === "active").length > 0 &&
                        selectedAlerts.size ===
                          alerts.filter((a) => a.status === "active").length
                      }
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((alert) => {
                  const typeConfig = ALERT_TYPE_CONFIG[alert.alert_type] || ALERT_TYPE_CONFIG.warning;
                  const statusConfig = STATUS_CONFIG[alert.status] || STATUS_CONFIG.active;
                  const TypeIcon = typeConfig.icon;
                  const StatusIcon = statusConfig.icon;

                  return (
                    <TableRow
                      key={alert.id}
                      className={cn(
                        alert.status === "active" && "bg-red-500/5"
                      )}
                    >
                      <TableCell>
                        {alert.status === "active" && (
                          <input
                            type="checkbox"
                            checked={selectedAlerts.has(alert.id)}
                            onChange={() => toggleAlertSelection(alert.id)}
                            className="rounded"
                          />
                        )}
                      </TableCell>
                      <TableCell className="font-medium">
                        {alert.provider_name}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <TypeIcon className={cn("h-4 w-4", typeConfig.color)} />
                          <span className={typeConfig.color}>{typeConfig.label}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{alert.threshold_percent}%</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusConfig.variant} className="gap-1">
                          <StatusIcon className="h-3 w-3" />
                          {statusConfig.label}
                        </Badge>
                        {alert.escalation_count && alert.escalation_count > 0 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Escalated {alert.escalation_count}x
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="max-w-[300px] truncate text-sm text-muted-foreground">
                        {alert.message}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(alert.created_at).toLocaleString()}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {alert.status === "active" && (
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => acknowledgeAlert(alert.id)}
                              className="h-7 text-xs"
                            >
                              Ack
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => resolveAlert(alert.id)}
                              className="h-7 text-xs"
                            >
                              Resolve
                            </Button>
                          </div>
                        )}
                        {alert.status === "acknowledged" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => resolveAlert(alert.id)}
                            className="h-7 text-xs"
                          >
                            Resolve
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
