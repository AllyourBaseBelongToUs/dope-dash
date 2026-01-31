import type { ErrorEvent } from '@/types';
import { useDashboardStore } from '@/store/dashboardStore';
import { ErrorDetailModal } from './ErrorDetailModal';
import { useState } from 'react';
import { AlertCircle, AlertTriangle, X, ChevronDown, ChevronUp } from 'lucide-react';

interface ErrorNotificationProps {
  sessionId?: string;
  maxErrors?: number;
}

export function ErrorNotification({ sessionId, maxErrors = 5 }: ErrorNotificationProps) {
  const {
    getSessionErrors,
    getActiveErrors,
    dismissError,
  } = useDashboardStore();

  const [selectedError, setSelectedError] = useState<ErrorEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  // Get errors - filtered by session if provided, otherwise show all active errors
  const errors = sessionId
    ? getSessionErrors(sessionId).slice(0, maxErrors)
    : getActiveErrors().slice(0, maxErrors);

  const errorCount = errors.length;

  if (errorCount === 0) return null;

  const handleDismiss = (errorId: string) => {
    dismissError(errorId);
    if (selectedError?.id === errorId) {
      setIsModalOpen(false);
      setSelectedError(null);
    }
  };

  const handleErrorClick = (error: ErrorEvent) => {
    setSelectedError(error);
    setIsModalOpen(true);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      <div className="bg-card border border-border rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div
          className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center gap-2">
            <div className="bg-red-950/50 p-2 rounded-md">
              <AlertCircle className="h-4 w-4 text-red-500" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                {errorCount === 1 ? '1 Error' : `${errorCount} Errors`}
              </h3>
              <p className="text-xs text-muted-foreground">
                {sessionId ? 'Session errors' : 'Active errors'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Error List */}
        {isExpanded && (
          <div className="border-t border-border divide-y divide-border max-h-96 overflow-y-auto">
            {errors.map((error) => (
              <div
                key={error.id}
                className="p-3 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => handleErrorClick(error)}
              >
                <div className="flex items-start gap-3">
                  {error.eventType === 'error' ? (
                    <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {error.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(error.createdAt)}
                      </span>
                      <span className="text-xs text-muted-foreground font-mono">
                        {error.sessionId.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDismiss(error.id);
                    }}
                    className="p-1 hover:bg-muted rounded-md transition-colors flex-shrink-0"
                    aria-label="Dismiss error"
                  >
                    <X className="h-3 w-3 text-muted-foreground" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Error Detail Modal */}
      <ErrorDetailModal
        error={selectedError}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedError(null);
        }}
        onDismiss={handleDismiss}
        allErrors={errors}
      />
    </>
  );
}
