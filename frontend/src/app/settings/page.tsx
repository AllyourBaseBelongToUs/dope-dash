'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { useEnvironmentStore } from '@/store/environmentStore';
import { useConnectionSettingsStore } from '@/store/connectionSettingsStore';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Bell,
  Volume2,
  VolumeX,
  BellOff,
  AlertCircle,
  Settings as SettingsIcon,
  Link,
  Info,
  Save,
  RotateCcw,
  Download,
  Upload,
  Search,
  Eye,
  EyeOff,
  Check,
  X,
  FileUp,
  AlertTriangle,
} from 'lucide-react';
import { NotificationPreference } from '@/types';
import { useToast } from '@/components/ui/use-toast';
import {
  exportSettings,
  downloadSettings,
  parseImportedSettings,
  readFileAsText,
  getDefaultConnectionSettings,
} from '@/utils/settingsExportImport';
import type { ConnectionSettings } from '@/store/connectionSettingsStore';
import type { NotificationSettings } from '@/types';

interface PreviewChange {
  category: 'notifications' | 'connections';
  field: string;
  label: string;
  oldValue: string | boolean | number;
  newValue: string | boolean | number;
}

export default function SettingsPage() {
  const { settings, toggleSound, toggleDesktop, setPreference, requestPermission, updateSettings } = useNotificationStore();
  const environmentConfig = useEnvironmentStore((state) => state.config);
  const {
    settings: connectionSettings,
    updateSettings: updateConnectionSettings,
    resetToDefaults,
  } = useConnectionSettingsStore();

  const { toast } = useToast();

  const [mounted, setMounted] = useState(false);
  const [hasNotificationPermission, setHasNotificationPermission] = useState(false);
  const [connectionUrls, setConnectionUrls] = useState<ConnectionSettings>({
    wsUrl: '',
    apiUrl: '',
    controlApiUrl: '',
    analyticsApiUrl: '',
  });
  const [hasChanges, setHasChanges] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Preview mode state
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [previewChanges, setPreviewChanges] = useState<PreviewChange[]>([]);
  const [pendingNotificationSettings, setPendingNotificationSettings] = useState<NotificationSettings | null>(null);
  const [pendingConnectionSettings, setPendingConnectionSettings] = useState<ConnectionSettings | null>(null);

  // Import state
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    if ('Notification' in window) {
      setHasNotificationPermission(Notification.permission === 'granted');
    }
  }, []);

  useEffect(() => {
    if (connectionSettings) {
      setConnectionUrls({
        wsUrl: connectionSettings.wsUrl || '',
        apiUrl: connectionSettings.apiUrl || '',
        controlApiUrl: connectionSettings.controlApiUrl || '',
        analyticsApiUrl: connectionSettings.analyticsApiUrl || '',
      });
    }
  }, [connectionSettings]);

  if (!mounted) {
    return null;
  }

  const handleRequestNotificationPermission = async () => {
    const granted = await requestPermission();
    setHasNotificationPermission(granted);
  };

  const handleUrlChange = (key: keyof typeof connectionUrls, value: string) => {
    const newValue = { ...connectionUrls, [key]: value };
    setConnectionUrls(newValue);

    if (isPreviewMode) {
      updatePreviewChanges('connections', key, value);
    } else {
      setHasChanges(true);
    }
  };

  const handleNotificationSettingChange = (updates: Partial<NotificationSettings>) => {
    const newSettings = { ...settings, ...updates };

    if (isPreviewMode) {
      setPendingNotificationSettings(newSettings);
      Object.entries(updates).forEach(([key, value]) => {
        updatePreviewChanges('notifications', key, value);
      });
    } else {
      updateSettings(updates);
    }
  };

  const updatePreviewChanges = (category: 'notifications' | 'connections', field: string, newValue: any) => {
    const oldValue = category === 'notifications'
      ? (pendingNotificationSettings || settings)[field as keyof NotificationSettings]
      : (pendingConnectionSettings || connectionUrls)[field as keyof ConnectionSettings];

    // Skip if no actual change
    if (oldValue === newValue) {
      return;
    }

    const labelMap: Record<string, string> = {
      soundEnabled: 'Sound Notifications',
      desktopEnabled: 'Desktop Notifications',
      preferences: 'Notification Level',
      wsUrl: 'WebSocket URL',
      apiUrl: 'API URL',
      controlApiUrl: 'Control API URL',
      analyticsApiUrl: 'Analytics API URL',
    };

    setPreviewChanges((prev) => {
      const existingIndex = prev.findIndex((c) => c.category === category && c.field === field);
      const newChange: PreviewChange = {
        category,
        field,
        label: labelMap[field] || field,
        oldValue,
        newValue,
      };

      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = newChange;
        return updated;
      }

      return [...prev, newChange];
    });
  };

  const handleSaveConnectionSettings = () => {
    updateConnectionSettings(connectionUrls);
    setHasChanges(false);
    toast({
      title: 'Settings saved',
      description: 'Your connection settings have been updated.',
    });
  };

  const handleResetConnectionSettings = () => {
    resetToDefaults();
    setHasChanges(false);
    toast({
      title: 'Settings reset',
      description: 'Connection settings have been reset to defaults.',
    });
  };

  const handleExportSettings = () => {
    try {
      const jsonSettings = exportSettings(settings, connectionUrls);
      downloadSettings(jsonSettings);
      toast({
        title: 'Settings exported',
        description: 'Your settings have been downloaded successfully.',
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'Failed to export settings',
        variant: 'destructive',
      });
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const content = await readFileAsText(file);
      const result = parseImportedSettings(content);

      if (!result.success || !result.settings) {
        toast({
          title: 'Import failed',
          description: result.error || 'Failed to import settings',
          variant: 'destructive',
        });
        return;
      }

      // Apply imported settings
      updateSettings(result.settings.settings.notifications);
      updateConnectionSettings(result.settings.settings.connections);

      toast({
        title: 'Settings imported',
        description: 'Your settings have been imported successfully.',
      });
    } catch (error) {
      toast({
        title: 'Import failed',
        description: error instanceof Error ? error.message : 'Failed to read file',
        variant: 'destructive',
      });
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleTogglePreviewMode = () => {
    if (isPreviewMode) {
      // Cancel preview mode - discard changes
      setIsPreviewMode(false);
      setPreviewChanges([]);
      setPendingNotificationSettings(null);
      setPendingConnectionSettings(null);
    } else {
      // Enter preview mode
      setIsPreviewMode(true);
      setPendingNotificationSettings({ ...settings });
      setPendingConnectionSettings({ ...connectionUrls });
      setPreviewChanges([]);
    }
  };

  const handleApplyPreviewChanges = () => {
    // Apply notification settings
    if (pendingNotificationSettings) {
      updateSettings(pendingNotificationSettings);
    }

    // Apply connection settings
    if (pendingConnectionSettings) {
      updateConnectionSettings(pendingConnectionSettings);
    }

    setIsPreviewMode(false);
    setPreviewChanges([]);
    setPendingNotificationSettings(null);
    setPendingConnectionSettings(null);
    setHasChanges(false);

    toast({
      title: 'Changes applied',
      description: `${previewChanges.length} setting(s) have been updated.`,
    });
  };

  // Filter functionality
  const filteredContent = useMemo(() => {
    if (!searchQuery.trim()) {
      return {
        notifications: true,
        connections: true,
        about: true,
      };
    }

    const query = searchQuery.toLowerCase();

    // Check if any notification settings match
    const notificationMatches = [
      'desktop notifications',
      'sound notifications',
      'notification level',
      'all',
      'errors',
      'none',
      'bell',
      'volume',
      'alert',
    ].some((term) => term.includes(query));

    // Check if any connection settings match
    const connectionMatches = [
      'websocket',
      'api',
      'control',
      'analytics',
      'url',
      'connection',
      'ws',
      'http',
      'localhost',
    ].some((term) => term.includes(query));

    // Check if about content matches
    const aboutMatches = [
      'version',
      'license',
      'build',
      'framework',
      'features',
      'technologies',
      'react',
      'typescript',
      'nextjs',
      'zustand',
      'radix',
    ].some((term) => term.includes(query));

    return {
      notifications: notificationMatches,
      connections: connectionMatches,
      about: aboutMatches,
    };
  }, [searchQuery]);

  const preferenceOptions: { value: NotificationPreference; label: string; icon: React.ReactNode }[] = [
    { value: 'all', label: 'All notifications', icon: <Bell className="h-4 w-4" /> },
    { value: 'errors', label: 'Errors only', icon: <AlertCircle className="h-4 w-4" /> },
    { value: 'none', label: 'None', icon: <BellOff className="h-4 w-4" /> },
  ];

  const connectionFields = [
    { key: 'wsUrl' as const, label: 'WebSocket URL', placeholder: 'ws://localhost:8001/ws' },
    { key: 'apiUrl' as const, label: 'API URL', placeholder: 'http://localhost:8001/api/events' },
    { key: 'controlApiUrl' as const, label: 'Control API URL', placeholder: 'http://localhost:8002' },
    { key: 'analyticsApiUrl' as const, label: 'Analytics API URL', placeholder: 'http://localhost:8004' },
  ];

  const highlightMatch = (text: string) => {
    if (!searchQuery.trim()) return text;

    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <main className="min-h-screen bg-background">
      {/* Header with Breadcrumb */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center space-x-2 text-sm text-muted-foreground mb-2">
            <a href="/" className="hover:text-foreground transition-colors">
              Home
            </a>
            <span>/</span>
            <span className="text-foreground font-medium">Settings</span>
          </nav>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <SettingsIcon className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Settings</h1>
                <p className="text-xs text-muted-foreground">Configure your dashboard preferences and connections</p>
              </div>
            </div>

            {/* Export/Import Buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportSettings}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleImportClick}
                className="gap-2"
              >
                <Upload className="h-4 w-4" />
                Import
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search settings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Preview Mode Banner */}
        {isPreviewMode && (
          <div className="mb-6 rounded-lg border-2 border-primary bg-primary/5 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Eye className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium text-foreground">Preview Mode</p>
                  <p className="text-sm text-muted-foreground">
                    Review your changes before applying them
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTogglePreviewMode}
                  className="gap-2"
                >
                  <X className="h-4 w-4" />
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleApplyPreviewChanges}
                  disabled={previewChanges.length === 0}
                  className="gap-2"
                >
                  <Check className="h-4 w-4" />
                  Apply {previewChanges.length} Change{previewChanges.length !== 1 ? 's' : ''}
                </Button>
              </div>
            </div>

            {/* Changes List */}
            {previewChanges.length > 0 && (
              <div className="mt-4 space-y-2">
                {previewChanges.map((change, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded bg-background p-3 text-sm"
                  >
                    <span className="font-medium">{change.label}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-muted-foreground">
                        {String(change.oldValue)}
                      </span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-medium text-primary">
                        {String(change.newValue)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Preview Mode Toggle */}
        {!isPreviewMode && (
          <div className="mb-6 flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTogglePreviewMode}
              className="gap-2"
            >
              <Eye className="h-4 w-4" />
              Preview Changes
            </Button>
          </div>
        )}

        {/* No Results Message */}
        {searchQuery && !filteredContent.notifications && !filteredContent.connections && !filteredContent.about && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <AlertTriangle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No results found</h3>
            <p className="text-sm text-muted-foreground">
              Try adjusting your search query to find what you're looking for.
            </p>
          </div>
        )}

        <Tabs defaultValue="notifications" className="w-full">
          <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
            <TabsTrigger
              value="notifications"
              disabled={!filteredContent.notifications && !!searchQuery}
            >
              <Bell className="h-4 w-4 mr-2" />
              Notifications
            </TabsTrigger>
            <TabsTrigger
              value="connections"
              disabled={!filteredContent.connections && !!searchQuery}
            >
              <Link className="h-4 w-4 mr-2" />
              Connections
            </TabsTrigger>
            <TabsTrigger
              value="about"
              disabled={!filteredContent.about && !!searchQuery}
            >
              <Info className="h-4 w-4 mr-2" />
              About
            </TabsTrigger>
          </TabsList>

          {/* Notifications Tab */}
          {filteredContent.notifications && (
            <TabsContent value="notifications" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>{highlightMatch('Notification Preferences')}</CardTitle>
                  <CardDescription>
                    Choose how you want to receive notifications from the dashboard
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Desktop Notifications */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="desktop-notifications" className="text-base">
                        {highlightMatch('Desktop Notifications')}
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Show browser notifications for events
                      </p>
                    </div>
                    <Switch
                      id="desktop-notifications"
                      checked={isPreviewMode ? pendingNotificationSettings?.desktopEnabled : settings.desktopEnabled}
                      onCheckedChange={(checked) => handleNotificationSettingChange({ desktopEnabled: checked })}
                      disabled={isPreviewMode}
                    />
                  </div>

                  {/* Request Permission Button */}
                  {!hasNotificationPermission && settings.desktopEnabled && (
                    <div className="rounded-lg bg-muted p-4">
                      <p className="text-sm mb-2">
                        Desktop notifications require browser permission.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRequestNotificationPermission}
                      >
                        <Bell className="h-4 w-4 mr-2" />
                        Enable Permissions
                      </Button>
                    </div>
                  )}

                  {/* Sound Notifications */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="sound-notifications" className="text-base">
                        {highlightMatch('Sound Notifications')}
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Play sound for new notifications
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {(isPreviewMode ? pendingNotificationSettings?.soundEnabled : settings.soundEnabled) ? (
                        <Volume2 className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <VolumeX className="h-4 w-4 text-muted-foreground" />
                      )}
                      <Switch
                        id="sound-notifications"
                        checked={isPreviewMode ? pendingNotificationSettings?.soundEnabled : settings.soundEnabled}
                        onCheckedChange={(checked) => handleNotificationSettingChange({ soundEnabled: checked })}
                        disabled={isPreviewMode}
                      />
                    </div>
                  </div>

                  {/* Preference Level */}
                  <div className="space-y-3">
                    <Label className="text-base">{highlightMatch('Notification Level')}</Label>
                    <div className="grid gap-3">
                      {preferenceOptions.map((option) => (
                        <div
                          key={option.value}
                          className={`flex items-center justify-between p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                            (isPreviewMode ? pendingNotificationSettings?.preferences : settings.preferences) === option.value
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:bg-muted/50'
                          }`}
                          onClick={() => isPreviewMode && handleNotificationSettingChange({ preferences: option.value })}
                        >
                          <div className="flex items-center gap-3">
                            {option.icon}
                            <span className="font-medium">{option.label}</span>
                          </div>
                          {(isPreviewMode ? pendingNotificationSettings?.preferences : settings.preferences) === option.value && (
                            <div className="h-2 w-2 rounded-full bg-primary" />
                          )}
                        </div>
                      ))}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {(isPreviewMode ? pendingNotificationSettings?.preferences : settings.preferences) === 'all' && 'Receive notifications for all events'}
                      {(isPreviewMode ? pendingNotificationSettings?.preferences : settings.preferences) === 'errors' && 'Only receive notifications for errors and failures'}
                      {(isPreviewMode ? pendingNotificationSettings?.preferences : settings.preferences) === 'none' && 'Disable all notifications'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Connections Tab */}
          {filteredContent.connections && (
            <TabsContent value="connections" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>{highlightMatch('API Connections')}</CardTitle>
                  <CardDescription>
                    Configure the URLs for connecting to backend services
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {connectionFields.map((field) => (
                    <div key={field.key} className="space-y-2">
                      <Label htmlFor={field.key}>{highlightMatch(field.label)}</Label>
                      <Input
                        id={field.key}
                        type="text"
                        placeholder={field.placeholder}
                        value={connectionUrls[field.key]}
                        onChange={(e) => handleUrlChange(field.key, e.target.value)}
                      />
                    </div>
                  ))}

                  {/* Current Environment Info */}
                  {environmentConfig && (
                    <div className="rounded-lg bg-muted p-4 space-y-2">
                      <p className="text-sm font-medium">Current Environment Configuration</p>
                      <div className="grid gap-1 text-sm text-muted-foreground">
                        <p>WebSocket: <code className="bg-background px-1 py-0.5 rounded">{environmentConfig.wsUrl}</code></p>
                        <p>API: <code className="bg-background px-1 py-0.5 rounded">{environmentConfig.apiUrl}</code></p>
                        <p>Control: <code className="bg-background px-1 py-0.5 rounded">{environmentConfig.controlApiUrl}</code></p>
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  {!isPreviewMode && (
                    <div className="flex gap-2">
                      <Button
                        onClick={handleSaveConnectionSettings}
                        disabled={!hasChanges}
                        className="flex-1"
                      >
                        <Save className="h-4 w-4 mr-2" />
                        Save Changes
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleResetConnectionSettings}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset to Defaults
                      </Button>
                    </div>
                  )}

                  {hasChanges && !isPreviewMode && (
                    <p className="text-sm text-muted-foreground">
                      You have unsaved changes. Click "Save Changes" to apply them.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* About Tab */}
          {filteredContent.about && (
            <TabsContent value="about" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>About Dope Dash</CardTitle>
                  <CardDescription>
                    Real-time multi-agent control center for Ralph Wiggum
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Version</span>
                      <span className="text-sm font-medium">0.1.0</span>
                    </div>
                    <div className="flex items-center justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">License</span>
                      <span className="text-sm font-medium">MIT</span>
                    </div>
                    <div className="flex items-center justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Build</span>
                      <span className="text-sm font-medium">Next.js 15.1.3</span>
                    </div>
                    <div className="flex items-center justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">UI Framework</span>
                      <span className="text-sm font-medium">shadcn/ui + Radix UI</span>
                    </div>
                    <div className="flex items-center justify-between py-2">
                      <span className="text-sm text-muted-foreground">State Management</span>
                      <span className="text-sm font-medium">Zustand</span>
                    </div>
                  </div>

                  <div className="rounded-lg bg-muted p-4 space-y-2">
                    <p className="text-sm font-medium">Features</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      <li>• Real-time WebSocket connections</li>
                      <li>• Multi-agent session monitoring</li>
                      <li>• Desktop notifications with sound</li>
                      <li>• Environment-aware configuration</li>
                      <li>• Command history and replay</li>
                      <li>• Analytics and reporting</li>
                      <li>• Project portfolio management</li>
                    </ul>
                  </div>

                  <div className="rounded-lg bg-muted p-4 space-y-2">
                    <p className="text-sm font-medium">Technologies</p>
                    <div className="flex flex-wrap gap-2">
                      {['React 19', 'TypeScript', 'Tailwind CSS', 'Next.js', 'Zustand', 'Radix UI', 'Recharts'].map((tech) => (
                        <span
                          key={tech}
                          className="text-xs px-2 py-1 rounded-full bg-background border"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </main>
  );
}
