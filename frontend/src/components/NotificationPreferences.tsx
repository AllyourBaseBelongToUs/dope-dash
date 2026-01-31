'use client';

import { Bell, BellOff, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useNotificationStore } from '@/store/notificationStore';
import { getNotificationService } from '@/services/notificationService';
import { useEffect, useState } from 'react';

export function NotificationPreferences() {
  const { settings, setPreference, toggleDesktop, unreadCount, requestPermission } = useNotificationStore();
  const [mounted, setMounted] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const service = getNotificationService();
    setPermissionGranted(service.isDesktopPermitted());
  }, []);

  if (!mounted) {
    return null;
  }

  const handleRequestPermission = async () => {
    const granted = await requestPermission();
    setPermissionGranted(granted);
  };

  const preferenceLabels = {
    all: 'All notifications',
    errors: 'Errors only',
    none: 'None',
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          {unreadCount > 0 ? (
            <>
              <Bell className="h-4 w-4" />
              <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-[10px] font-medium flex items-center justify-center text-destructive-foreground">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            </>
          ) : settings.preferences === 'none' || !settings.desktopEnabled ? (
            <BellOff className="h-4 w-4" />
          ) : (
            <Bell className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setPreference('all')}>
          <Bell className="mr-2 h-4 w-4" />
          <span>All events</span>
          {settings.preferences === 'all' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setPreference('errors')}>
          <AlertCircle className="mr-2 h-4 w-4" />
          <span>Errors only</span>
          {settings.preferences === 'errors' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setPreference('none')}>
          <BellOff className="mr-2 h-4 w-4" />
          <span>None</span>
          {settings.preferences === 'none' && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={toggleDesktop}>
          <span className="mr-2">Desktop</span>
          <span className="ml-auto text-xs text-muted-foreground">
            {settings.desktopEnabled ? 'On' : 'Off'}
          </span>
        </DropdownMenuItem>
        {!permissionGranted && getNotificationService().isDesktopSupported() && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleRequestPermission}>
              Enable desktop notifications
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
