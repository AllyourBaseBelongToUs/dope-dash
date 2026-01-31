import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';
import { type ControlCommand } from '@/api/control';
import { Pause, Play, SkipForward, StopCircle } from 'lucide-react';

interface ControlButtonProps {
  command: ControlCommand;
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
}

export function ControlButton({
  command,
  disabled = false,
  loading = false,
  onClick,
  className,
}: ControlButtonProps) {
  const config = {
    pause: {
      label: 'Pause',
      icon: Pause,
      variant: 'secondary' as const,
      shortcut: 'Space',
    },
    resume: {
      label: 'Resume',
      icon: Play,
      variant: 'default' as const,
      shortcut: 'R',
    },
    skip: {
      label: 'Skip',
      icon: SkipForward,
      variant: 'outline' as const,
      shortcut: 'S',
    },
    stop: {
      label: 'Stop',
      icon: StopCircle,
      variant: 'destructive' as const,
      shortcut: 'Esc',
    },
  };

  const { label, icon: Icon, variant, shortcut } = config[command];

  return (
    <Button
      variant={variant}
      size="sm"
      disabled={disabled || loading}
      onClick={onClick}
      className={cn('gap-1.5', className)}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        <Icon className="h-4 w-4" />
      )}
      <span>{label}</span>
      {!loading && (
        <kbd className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
          {shortcut}
        </kbd>
      )}
    </Button>
  );
}
