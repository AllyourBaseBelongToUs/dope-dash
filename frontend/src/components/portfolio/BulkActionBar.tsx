import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Pause,
  Play,
  Square,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { usePortfolioStore } from '@/store/portfolioStore';
import type { ProjectControlAction } from '@/types';

interface BulkActionBarProps {
  selectedCount: number;
  onDeselectAll: () => void;
  onOperationComplete?: (result: {
    action: ProjectControlAction;
    total_requested: number;
    successful: number;
    failed: number;
    total_agents_affected: number;
  }) => void;
}

const bulkActions = {
  pause: {
    icon: Pause,
    label: 'Pause',
    description: 'Pause all selected projects. Agents will stop processing but remain available.',
    variant: 'outline' as const,
    destructive: false,
  },
  resume: {
    icon: Play,
    label: 'Resume',
    description: 'Resume all paused projects. Agents will continue processing.',
    variant: 'default' as const,
    destructive: false,
  },
  stop: {
    icon: Square,
    label: 'Stop',
    description: 'Stop all selected projects. This will terminate all active sessions.',
    variant: 'destructive' as const,
    destructive: true,
  },
};

export function BulkActionBar({
  selectedCount,
  onDeselectAll,
  onOperationComplete,
}: BulkActionBarProps) {
  const [pendingAction, setPendingAction] = useState<keyof typeof bulkActions | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const bulkPauseProjects = usePortfolioStore((state) => state.bulkPauseProjects);
  const bulkResumeProjects = usePortfolioStore((state) => state.bulkResumeProjects);
  const bulkStopProjects = usePortfolioStore((state) => state.bulkStopProjects);

  const executeBulkAction = async (action: keyof typeof bulkActions) => {
    setIsExecuting(true);
    try {
      let result;
      switch (action) {
        case 'pause':
          result = await bulkPauseProjects();
          break;
        case 'resume':
          result = await bulkResumeProjects();
          break;
        case 'stop':
          result = await bulkStopProjects();
          break;
      }

      if (result && onOperationComplete) {
        onOperationComplete({
          action: result.action,
          total_requested: result.total_requested,
          successful: result.successful,
          failed: result.failed,
          total_agents_affected: result.total_agents_affected,
        });
      }
    } finally {
      setIsExecuting(false);
      setPendingAction(null);
    }
  };

  const handleActionClick = (action: keyof typeof bulkActions, requiresConfirmation: boolean) => {
    if (requiresConfirmation) {
      setPendingAction(action);
    } else {
      executeBulkAction(action);
    }
  };

  const BulkActionButton = ({
    action,
  }: {
    action: keyof typeof bulkActions;
  }) => {
    const config = bulkActions[action];
    const Icon = config.icon;

    return (
      <Button
        variant={config.variant}
        size="sm"
        onClick={() => handleActionClick(action, config.destructive)}
        disabled={isExecuting}
        className="min-w-[100px]"
      >
        {isExecuting && pendingAction === action ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Icon className="h-4 w-4 mr-2" />
        )}
        {config.label} ({selectedCount})
      </Button>
    );
  };

  return (
    <>
      {/* Bulk Action Bar */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
        <div className="bg-background border border-border rounded-lg shadow-lg p-4 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="bg-primary/10 p-2 rounded-full">
              <CheckCircle2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-medium text-sm">{selectedCount} project{selectedCount !== 1 ? 's' : ''} selected</p>
              <p className="text-xs text-muted-foreground">Ready for bulk actions</p>
            </div>
          </div>

          <div className="h-8 w-px bg-border" />

          <div className="flex items-center gap-2">
            <BulkActionButton action="pause" />
            <BulkActionButton action="resume" />
            <BulkActionButton action="stop" />
          </div>

          <div className="h-8 w-px bg-border" />

          <Button
            variant="ghost"
            size="sm"
            onClick={onDeselectAll}
            disabled={isExecuting}
          >
            <X className="h-4 w-4 mr-2" />
            Clear
          </Button>
        </div>
      </div>

      {/* Confirmation Dialog for Destructive Actions */}
      {pendingAction && bulkActions[pendingAction].destructive && (
        <AlertDialog
          open={!!pendingAction}
          onOpenChange={(open) => {
            if (!open) setPendingAction(null);
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle asChild>
                <div className="flex items-center gap-2">
                  <Square className="h-5 w-5" />
                  <span>
                    Stop {selectedCount} project{selectedCount !== 1 ? 's' : ''}?
                  </span>
                </div>
              </AlertDialogTitle>
              <AlertDialogDescription>
                {bulkActions[pendingAction].description}
                <div className="mt-4 p-3 bg-destructive/10 rounded-md border border-destructive/20">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                    <div>
                      <strong>Warning:</strong> This will stop all agents in the selected projects.
                      Active sessions will be terminated.
                    </div>
                  </div>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isExecuting}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={(e) => {
                  e.preventDefault();
                  executeBulkAction(pendingAction!);
                }}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isExecuting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Stopping...
                  </>
                ) : (
                  'Stop Projects'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </>
  );
}
