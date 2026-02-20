"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
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
import { Bell, Volume2, Monitor, Save, RotateCcw, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEnvironmentStore } from "@/store/environmentStore";

interface AlertConfig {
  id: string;
  provider_id: string | null;
  project_id: string | null;
  warning_threshold: number;
  critical_threshold: number;
  emergency_threshold: number;
  channels: string[];
  dashboard_enabled: boolean;
  desktop_enabled: boolean;
  audio_enabled: boolean;
  cooldown_minutes: number;
  escalation_enabled: boolean;
  escalation_minutes: number;
  max_escalations: number;
  is_active: boolean;
}

interface Provider {
  id: string;
  name: string;
  display_name: string;
}

const DEFAULT_CONFIG: Omit<AlertConfig, "id"> = {
  provider_id: null,
  project_id: null,
  warning_threshold: 80,
  critical_threshold: 90,
  emergency_threshold: 95,
  channels: ["dashboard", "desktop", "audio"],
  dashboard_enabled: true,
  desktop_enabled: true,
  audio_enabled: true,
  cooldown_minutes: 30,
  escalation_enabled: true,
  escalation_minutes: 15,
  max_escalations: 3,
  is_active: true,
};

export function AlertConfigPanel() {
  const [configs, setConfigs] = useState<AlertConfig[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<AlertConfig | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const environmentConfig = useEnvironmentStore((state) => state.config);
  const API_URL = environmentConfig?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch configs and providers
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);

      const [configsRes, providersRes] = await Promise.all([
        fetch(`${API_URL}/api/quota/alerts/config?active_only=false`),
        fetch(`${API_URL}/api/quota/providers`),
      ]);

      if (configsRes.ok && providersRes.ok) {
        const [configsData, providersData] = await Promise.all([
          configsRes.json(),
          providersRes.json(),
        ]);
        setConfigs(configsData.items || []);
        setProviders(providersData.items || []);
      }
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  // Save config
  const saveConfig = async () => {
    if (!selectedConfig) return;

    try {
      setSaving(true);

      const isNew = !selectedConfig.id || selectedConfig.id === "new";
      const url = isNew
        ? `${API_URL}/api/quota/alerts/config`
        : `${API_URL}/api/quota/alerts/config/${selectedConfig.id}`;

      const method = isNew ? "POST" : "PATCH";

      const body = isNew
        ? {
            provider_id: selectedConfig.provider_id,
            project_id: selectedConfig.project_id,
            warning_threshold: selectedConfig.warning_threshold,
            critical_threshold: selectedConfig.critical_threshold,
            emergency_threshold: selectedConfig.emergency_threshold,
            channels: selectedConfig.channels,
            dashboard_enabled: selectedConfig.dashboard_enabled,
            desktop_enabled: selectedConfig.desktop_enabled,
            audio_enabled: selectedConfig.audio_enabled,
            cooldown_minutes: selectedConfig.cooldown_minutes,
            escalation_enabled: selectedConfig.escalation_enabled,
            escalation_minutes: selectedConfig.escalation_minutes,
            max_escalations: selectedConfig.max_escalations,
            is_active: selectedConfig.is_active,
          }
        : {
            warning_threshold: selectedConfig.warning_threshold,
            critical_threshold: selectedConfig.critical_threshold,
            emergency_threshold: selectedConfig.emergency_threshold,
            channels: selectedConfig.channels,
            dashboard_enabled: selectedConfig.dashboard_enabled,
            desktop_enabled: selectedConfig.desktop_enabled,
            audio_enabled: selectedConfig.audio_enabled,
            cooldown_minutes: selectedConfig.cooldown_minutes,
            escalation_enabled: selectedConfig.escalation_enabled,
            escalation_minutes: selectedConfig.escalation_minutes,
            max_escalations: selectedConfig.max_escalations,
            is_active: selectedConfig.is_active,
          };

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        setIsEditing(false);
        fetchData();
      }
    } catch (err) {
      console.error("Failed to save config:", err);
    } finally {
      setSaving(false);
    }
  };

  // Toggle channel
  const toggleChannel = (channel: string) => {
    if (!selectedConfig) return;

    const newChannels = selectedConfig.channels.includes(channel)
      ? selectedConfig.channels.filter((c) => c !== channel)
      : [...selectedConfig.channels, channel];

    setSelectedConfig({
      ...selectedConfig,
      channels: newChannels,
      dashboard_enabled: newChannels.includes("dashboard"),
      desktop_enabled: newChannels.includes("desktop"),
      audio_enabled: newChannels.includes("audio"),
    });
  };

  // Create new config
  const createNewConfig = () => {
    setSelectedConfig({
      ...DEFAULT_CONFIG,
      id: "new",
    });
    setIsEditing(true);
  };

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">Loading alert settings...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Config List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Alert Settings
              </CardTitle>
              <CardDescription>
                Configure alert thresholds, channels, and escalation
              </CardDescription>
            </div>
            <Button onClick={createNewConfig} size="sm">
              <Plus className="h-4 w-4 mr-1" />
              Add Config
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <div className="space-y-2">
            {configs.map((config) => (
              <div
                key={config.id}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors",
                  selectedConfig?.id === config.id && "bg-muted border-primary"
                )}
                onClick={() => {
                  setSelectedConfig(config);
                  setIsEditing(false);
                }}
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="font-medium">
                      {config.provider_id
                        ? providers.find((p) => p.id === config.provider_id)?.display_name ||
                          "Unknown Provider"
                        : "Global Settings"}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Warn: {config.warning_threshold}% | Critical: {config.critical_threshold}% | Emergency:{" "}
                      {config.emergency_threshold}%
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {config.dashboard_enabled && (
                    <Badge variant="outline" className="text-xs">
                      Dashboard
                    </Badge>
                  )}
                  {config.desktop_enabled && (
                    <Badge variant="outline" className="text-xs">
                      <Monitor className="h-3 w-3 mr-1" />
                      Desktop
                    </Badge>
                  )}
                  {config.audio_enabled && (
                    <Badge variant="outline" className="text-xs">
                      <Volume2 className="h-3 w-3 mr-1" />
                      Audio
                    </Badge>
                  )}
                  {!config.is_active && (
                    <Badge variant="secondary">Inactive</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Config Editor */}
      {selectedConfig && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">
                {isEditing ? "Edit Settings" : "Settings Details"}
              </CardTitle>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsEditing(false);
                        if (selectedConfig.id === "new") {
                          setSelectedConfig(null);
                        }
                      }}
                    >
                      Cancel
                    </Button>
                    <Button size="sm" onClick={saveConfig} disabled={saving}>
                      <Save className="h-4 w-4 mr-1" />
                      {saving ? "Saving..." : "Save"}
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsEditing(true)}
                    >
                      Edit
                    </Button>
                    {selectedConfig.id !== "new" && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="destructive" size="sm">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Configuration</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete this alert configuration?
                              This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => {
                                // Delete logic here
                                setSelectedConfig(null);
                              }}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                  </>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Provider Selection (for new configs) */}
            {isEditing && selectedConfig.id === "new" && (
              <div className="space-y-2">
                <Label>Provider (optional)</Label>
                <Select
                  value={selectedConfig.provider_id || "global"}
                  onValueChange={(value) =>
                    setSelectedConfig({
                      ...selectedConfig,
                      provider_id: value === "global" ? null : value,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="global">Global (All Providers)</SelectItem>
                    {providers.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Thresholds */}
            <div className="space-y-4">
              <Label className="text-base">Thresholds (%)</Label>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="warning" className="text-yellow-500">
                    Warning
                  </Label>
                  <Input
                    id="warning"
                    type="number"
                    min={0}
                    max={100}
                    value={selectedConfig.warning_threshold}
                    onChange={(e) =>
                      setSelectedConfig({
                        ...selectedConfig,
                        warning_threshold: parseInt(e.target.value) || 0,
                      })
                    }
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="critical" className="text-orange-500">
                    Critical
                  </Label>
                  <Input
                    id="critical"
                    type="number"
                    min={0}
                    max={100}
                    value={selectedConfig.critical_threshold}
                    onChange={(e) =>
                      setSelectedConfig({
                        ...selectedConfig,
                        critical_threshold: parseInt(e.target.value) || 0,
                      })
                    }
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emergency" className="text-red-500">
                    Emergency
                  </Label>
                  <Input
                    id="emergency"
                    type="number"
                    min={0}
                    max={100}
                    value={selectedConfig.emergency_threshold}
                    onChange={(e) =>
                      setSelectedConfig({
                        ...selectedConfig,
                        emergency_threshold: parseInt(e.target.value) || 0,
                      })
                    }
                    disabled={!isEditing}
                  />
                </div>
              </div>
            </div>

            {/* Alert Channels */}
            <div className="space-y-4">
              <Label className="text-base">Alert Channels</Label>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: "dashboard", label: "Dashboard", icon: Bell },
                  { id: "desktop", label: "Desktop", icon: Monitor },
                  { id: "audio", label: "Audio (95%+)", icon: Volume2 },
                ].map(({ id, label, icon: Icon }) => (
                  <Button
                    key={id}
                    variant={selectedConfig.channels.includes(id) ? "default" : "outline"}
                    size="sm"
                    onClick={() => isEditing && toggleChannel(id)}
                    disabled={!isEditing}
                    className="gap-2"
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Cooldown */}
            <div className="space-y-2">
              <Label htmlFor="cooldown">Cooldown Period (minutes)</Label>
              <Input
                id="cooldown"
                type="number"
                min={0}
                max={1440}
                value={selectedConfig.cooldown_minutes}
                onChange={(e) =>
                  setSelectedConfig({
                    ...selectedConfig,
                    cooldown_minutes: parseInt(e.target.value) || 0,
                  })
                }
                disabled={!isEditing}
              />
              <p className="text-xs text-muted-foreground">
                Minimum time between alerts for the same threshold
              </p>
            </div>

            {/* Escalation Settings */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="escalation" className="text-base">
                  Escalation
                </Label>
                <Switch
                  id="escalation"
                  checked={selectedConfig.escalation_enabled}
                  onCheckedChange={(checked) =>
                    setSelectedConfig({
                      ...selectedConfig,
                      escalation_enabled: checked,
                    })
                  }
                  disabled={!isEditing}
                />
              </div>

              {selectedConfig.escalation_enabled && (
                <div className="grid grid-cols-2 gap-4 pl-4 border-l-2 border-muted">
                  <div className="space-y-2">
                    <Label htmlFor="escalation-minutes">
                      Escalation After (minutes)
                    </Label>
                    <Input
                      id="escalation-minutes"
                      type="number"
                      min={1}
                      max={1440}
                      value={selectedConfig.escalation_minutes}
                      onChange={(e) =>
                        setSelectedConfig({
                          ...selectedConfig,
                          escalation_minutes: parseInt(e.target.value) || 15,
                        })
                      }
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max-escalations">Max Escalations</Label>
                    <Input
                      id="max-escalations"
                      type="number"
                      min={0}
                      max={10}
                      value={selectedConfig.max_escalations}
                      onChange={(e) =>
                        setSelectedConfig({
                          ...selectedConfig,
                          max_escalations: parseInt(e.target.value) || 3,
                        })
                      }
                      disabled={!isEditing}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Active Status */}
            <div className="flex items-center justify-between">
              <Label htmlFor="active" className="text-base">
                Active
              </Label>
              <Switch
                id="active"
                checked={selectedConfig.is_active}
                onCheckedChange={(checked) =>
                  setSelectedConfig({
                    ...selectedConfig,
                    is_active: checked,
                  })
                }
                disabled={!isEditing}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
