import type { ErrorEvent } from '@/types';
import { X, Copy, Download, AlertCircle, AlertTriangle } from 'lucide-react';
import { exportLocalErrorsToCSV } from '@/utils/exportErrors';

interface ErrorDetailModalProps {
  error: ErrorEvent | null;
  isOpen: boolean;
  onClose: () => void;
  onDismiss: (errorId: string) => void;
  onExport?: () => void;
  allErrors?: ErrorEvent[];
}

export function ErrorDetailModal({
  error,
  isOpen,
  onClose,
  onDismiss,
  onExport,
  allErrors,
}: ErrorDetailModalProps) {
  if (!isOpen || !error) return null;

  const handleCopyError = () => {
    const text = `Error: ${error.message}\n\nStack Trace:\n${error.stackTrace || 'N/A'}\n\nData: ${JSON.stringify(error.data, null, 2)}`;
    navigator.clipboard.writeText(text);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            {error.eventType === 'error' ? (
              <AlertCircle className="h-5 w-5 text-red-500" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                {error.eventType === 'error' ? 'Error' : 'Spec Failure'} Details
              </h2>
              <p className="text-xs text-muted-foreground font-mono">
                {error.id.slice(0, 8)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded-md transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Error Message */}
          <div>
            <label className="text-sm font-medium text-muted-foreground block mb-2">
              Error Message
            </label>
            <div className="bg-muted p-3 rounded-md border border-border">
              <p className="text-sm text-foreground font-mono break-words">
                {error.message}
              </p>
            </div>
          </div>

          {/* Timestamp */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Event Type
              </label>
              <div className="bg-muted p-3 rounded-md border border-border">
                <p className="text-sm text-foreground font-mono">
                  {error.eventType}
                </p>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Timestamp
              </label>
              <div className="bg-muted p-3 rounded-md border border-border">
                <p className="text-sm text-foreground">
                  {formatTimestamp(error.createdAt)}
                </p>
              </div>
            </div>
          </div>

          {/* Stack Trace */}
          {error.stackTrace && (
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Stack Trace
              </label>
              <div className="bg-muted p-3 rounded-md border border-border overflow-x-auto">
                <pre className="text-xs text-red-400 font-mono whitespace-pre-wrap break-words">
                  {error.stackTrace}
                </pre>
              </div>
            </div>
          )}

          {/* Session ID */}
          <div>
            <label className="text-sm font-medium text-muted-foreground block mb-2">
              Session ID
            </label>
            <div className="bg-muted p-3 rounded-md border border-border">
              <p className="text-sm text-foreground font-mono break-all">
                {error.sessionId}
              </p>
            </div>
          </div>

          {/* Additional Data */}
          {Object.keys(error.data).length > 0 && (
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Additional Data
              </label>
              <div className="bg-muted p-3 rounded-md border border-border overflow-x-auto">
                <pre className="text-xs text-foreground font-mono">
                  {JSON.stringify(error.data, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between p-4 border-t border-border">
          <div className="flex gap-2">
            <button
              onClick={handleCopyError}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors"
            >
              <Copy className="h-4 w-4" />
              Copy
            </button>
            {onExport && (
              <button
                onClick={onExport}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors"
                title="Export this error to CSV"
              >
                <Download className="h-4 w-4" />
                Export Error
              </button>
            )}
            {allErrors && allErrors.length > 0 && (
              <button
                onClick={() => exportLocalErrorsToCSV(allErrors)}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors"
                title={`Export all ${allErrors.length} errors to CSV`}
              >
                <Download className="h-4 w-4" />
                Export All ({allErrors.length})
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onDismiss(error.id)}
              className="px-3 py-2 text-sm bg-red-950/50 hover:bg-red-950/80 text-red-400 rounded-md transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={onClose}
              className="px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
