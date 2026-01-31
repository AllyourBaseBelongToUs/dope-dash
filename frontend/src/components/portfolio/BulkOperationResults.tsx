import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ProjectControlAction } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface BulkOperationResultItem {
  project_id: string;
  project_name: string;
  success: boolean;
  message: string;
  agents_affected: number;
  error?: string;
}

interface BulkOperationResultsProps {
  action: ProjectControlAction;
  totalRequested: number;
  successful: number;
  failed: number;
  totalAgentsAffected: number;
  results: BulkOperationResultItem[];
  timestamp: Date;
  onClose: () => void;
  onUndo?: () => void;
}

const actionLabels: Record<ProjectControlAction, string> = {
  pause: 'Paused',
  resume: 'Resumed',
  skip: 'Skipped',
  stop: 'Stopped',
  retry: 'Retried',
  restart: 'Restarted',
};

export function BulkOperationResults({
  action,
  totalRequested,
  successful,
  failed,
  totalAgentsAffected,
  results,
  timestamp,
  onClose,
  onUndo,
}: BulkOperationResultsProps) {
  const actionLabel = actionLabels[action];

  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 w-full max-w-md">
      <div className="bg-background border border-border rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-muted/50 px-4 py-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {failed === 0 ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : successful === 0 ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-500" />
              )}
              <div>
                <p className="font-medium text-sm">
                  {failed === 0 ? 'Bulk operation completed' : 'Bulk operation completed with errors'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(timestamp, { addSuffix: true })}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Summary */}
        <div className="px-4 py-3 border-b border-border">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-primary">{totalRequested}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-500">{successful}</p>
              <p className="text-xs text-muted-foreground">{actionLabel}</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-500">{failed}</p>
              <p className="text-xs text-muted-foreground">Failed</p>
            </div>
          </div>
          {totalAgentsAffected > 0 && (
            <p className="text-xs text-center text-muted-foreground mt-2">
              {totalAgentsAffected} agent{totalAgentsAffected !== 1 ? 's' : ''} affected
            </p>
          )}
        </div>

        {/* Results List (show only failures, or first few if many) */}
        {(failed > 0 || results.length <= 5) && (
          <div className="max-h-60 overflow-y-auto">
            {results.slice(0, 10).map((result) => (
              <div
                key={result.project_id}
                className="px-4 py-2 border-b border-border last:border-0 flex items-start gap-3 hover:bg-muted/50 transition-colors"
              >
                {result.success ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{result.project_name}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {result.success
                      ? `${result.message} (${result.agents_affected} agents affected)`
                      : result.error || result.message}
                  </p>
                </div>
              </div>
            ))}
            {results.length > 10 && (
              <div className="px-4 py-2 text-center text-xs text-muted-foreground">
                +{results.length - 10} more projects
              </div>
            )}
          </div>
        )}

        {/* Footer with Undo option */}
        {onUndo && successful > 0 && (
          <div className="px-4 py-3 bg-muted/30 border-t border-border">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={onUndo}
            >
              Undo Operation
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
