'use client';

import { Volume2, VolumeX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNotificationStore } from '@/store/notificationStore';
import { useEffect, useState } from 'react';

interface SoundToggleButtonProps {
  className?: string;
}

export function SoundToggleButton({ className }: SoundToggleButtonProps) {
  const { settings, toggleSound } = useNotificationStore();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className={className}>
        <Volume2 className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className={className}
      onClick={toggleSound}
      title={settings.soundEnabled ? 'Sound notifications on' : 'Sound notifications off'}
    >
      {settings.soundEnabled ? (
        <Volume2 className="h-4 w-4" />
      ) : (
        <VolumeX className="h-4 w-4" />
      )}
    </Button>
  );
}
