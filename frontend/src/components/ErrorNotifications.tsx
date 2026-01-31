'use client';

import { useState } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { AlertCircle, AlertTriangle, X, Download, ChevronDown, ChevronUp } from 'lucide-react';
import type { ErrorEvent } from '@/types';

interface ErrorNotificationsProps {
  sessionId?: string;
}

export function ErrorNotifications({ sessionId }: ErrorNotificationsProps) {
  const { errors, dismissedErrors, dismissError, getActiveErrors, getSessionErrors } = useDashboardStore();
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const relevantErrors = sessionId ? getSessionErrors(sessionId) : getActiveErrors();
  const errorCount = relevantErrors.length;

  if (errorCount === 0) {
    return null;
  }

  const handleDismiss = (errorId: string) => {
    dismissError(errorId);
    if (expandedErrorId === errorId) {
      setExpandedErrorId(null);
    }
  };

  const handleDismissAll = () => {
    relevantErrors.forEach(error => dismissError(error.id));
    setExpandedErrorId(null);
  };

  const handleExportCSV = () => {
    const headers = ['Error ID', 'Session ID', 'Type', 'Message', 'Created At', 'Stack Trace'];
    const rows = relevantErrors.map(error => [
      error.id,
      error.sessionId,
      error.eventType,
      `"${error.message.replace(/"/g, '""')}"`,
      error.createdAt,
      `"${(error.stackTrace || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `errors_${new Date().toISOString()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <>
      {/* Error Summary Bar */}
      <div className="mb-4 bg-red-950/30 border border-red-900/50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="relative">
              <AlertCircle className="h-5 w-5 text-red-500" />
              {errorCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
                  {errorCount}
                </span>
              )}
            </div>
            <div>
              <h3 className="font-semibold text-red-400">
                {errorCount === 1 ? '1 Error' : `${errorCount} Errors`}
              </h3>
              <p className="text-xs text-red-300/70">
                Click to view details
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium text-red-300 hover:text-white hover:bg-red-900/50 rounded-md transition-colors"
            >
              View All
            </button>
            <button
              onClick={handleExportCSV}
              className="p-1.5 text-red-300 hover:text-white hover:bg-red-900/50 rounded-md transition-colors"
              title="Export to CSV"
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              onClick={handleDismissAll}
              className="px-3 py-1.5 text-xs font-medium text-red-300 hover:text-white hover:bg-red-900/50 rounded-md transition-colors"
            >
              Dismiss All
            </button>
          </div>
        </div>

        {/* Inline error list (first 3 errors) */}
        <div className="space-y-2">
          {relevantErrors.slice(0, 3).map((error) => (
            <ErrorItem
              key={error.id}
              error={error}
              isExpanded={expandedErrorId === error.id}
              onToggle={() => setExpandedErrorId(expandedErrorId === error.id ? null : error.id)}
              onDismiss={() => handleDismiss(error.id)}
            />
          ))}
          {errorCount > 3 && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="w-full text-center text-xs text-red-300 hover:text-white py-2"
            >
              View all {errorCount} errors
            </button>
          )}
        </div>
      </div>

      {/* Error Detail Modal */}
      {isModalOpen && (
        <ErrorModal
          errors={relevantErrors}
          onClose={() => setIsModalOpen(false)}
          onDismiss={handleDismiss}
          onDismissAll={handleDismissAll}
          onExport={handleExportCSV}
        />
      )}
    </>
  );
}

interface ErrorItemProps {
  error: ErrorEvent;
  isExpanded: boolean;
  onToggle: () => void;
  onDismiss: () => void;
}

function ErrorItem({ error, isExpanded, onToggle, onDismiss }: ErrorItemProps) {
  const getErrorIcon = () => {
    return error.eventType === 'spec_fail' ? (
      <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0" />
    ) : (
      <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
    );
  };

  return (
    <div className="bg-red-950/20 border border-red-900/30 rounded-md overflow-hidden">
      <div
        className="flex items-start gap-2 p-3 cursor-pointer hover:bg-red-950/30 transition-colors"
        onClick={onToggle}
      >
        {getErrorIcon()}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-red-300/70 capitalize">
              {error.eventType}
            </span>
            <span className="text-xs text-red-300/50">
              {new Date(error.createdAt).toLocaleTimeString()}
            </span>
          </div>
          <p className="text-sm text-red-300 mt-1 line-clamp-1">
            {error.message}
          </p>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-red-400 flex-shrink-0 mt-1" />
        ) : (
          <ChevronDown className="h-4 w-4 text-red-400 flex-shrink-0 mt-1" />
        )}
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-red-900/30">
          <div className="pt-2">
            <p className="text-sm text-red-200 whitespace-pre-wrap break-words">
              {error.message}
            </p>
            {error.stackTrace && (
              <details className="mt-2">
                <summary className="text-xs text-red-300/70 cursor-pointer hover:text-red-300">
                  Stack Trace
                </summary>
                <pre className="mt-2 p-2 bg-black/30 rounded text-xs text-red-300/80 overflow-x-auto">
                  {error.stackTrace}
                </pre>
              </details>
            )}
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-red-300/50 font-mono">
                ID: {error.id.slice(0, 8)}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss();
                }}
                className="flex items-center gap-1 px-2 py-1 text-xs text-red-300 hover:text-white hover:bg-red-900/50 rounded transition-colors"
              >
                <X className="h-3 w-3" />
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface ErrorModalProps {
  errors: ErrorEvent[];
  onClose: () => void;
  onDismiss: (errorId: string) => void;
  onDismissAll: () => void;
  onExport: () => void;
}

function ErrorModal({ errors, onClose, onDismiss, onDismissAll, onExport }: ErrorModalProps) {
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="bg-red-950/50 p-2 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Error Log</h2>
              <p className="text-sm text-muted-foreground">
                {errors.length} {errors.length === 1 ? 'error' : 'errors'} recorded
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onExport}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <button
              onClick={onDismissAll}
              className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            >
              Dismiss All
            </button>
            <button
              onClick={onClose}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Error List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {errors.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No errors to display</p>
            </div>
          ) : (
            errors.map((error) => (
              <div
                key={error.id}
                className="bg-red-950/20 border border-red-900/30 rounded-md overflow-hidden"
              >
                <div
                  className="flex items-start gap-2 p-3 cursor-pointer hover:bg-red-950/30 transition-colors"
                  onClick={() => setExpandedErrorId(expandedErrorId === error.id ? null : error.id)}
                >
                  {error.eventType === 'spec_fail' ? (
                    <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0 mt-1" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-1" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono text-red-300/70 capitalize">
                        {error.eventType}
                      </span>
                      <span className="text-xs text-red-300/50">
                        {new Date(error.createdAt).toLocaleString()}
                      </span>
                      <span className="text-xs font-mono text-red-300/50">
                        {error.sessionId.slice(0, 8)}
                      </span>
                    </div>
                    <p className="text-sm text-red-300 mt-1">
                      {error.message}
                    </p>
                  </div>
                  {expandedErrorId === error.id ? (
                    <ChevronUp className="h-4 w-4 text-red-400 flex-shrink-0 mt-1" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-red-400 flex-shrink-0 mt-1" />
                  )}
                </div>

                {expandedErrorId === error.id && (
                  <div className="px-3 pb-3 border-t border-red-900/30">
                    <div className="pt-2">
                      <p className="text-sm text-red-200 whitespace-pre-wrap break-words">
                        {error.message}
                      </p>
                      {error.stackTrace && (
                        <details className="mt-2" open>
                          <summary className="text-xs text-red-300/70 cursor-pointer hover:text-red-300">
                            Stack Trace
                          </summary>
                          <pre className="mt-2 p-3 bg-black/30 rounded text-xs text-red-300/80 overflow-x-auto">
                            {error.stackTrace}
                          </pre>
                        </details>
                      )}
                      <div className="mt-3 space-y-1">
                        <div className="text-xs text-red-300/50">
                          <span className="font-medium">Error ID:</span> {error.id}
                        </div>
                        <div className="text-xs text-red-300/50">
                          <span className="font-medium">Session ID:</span> {error.sessionId}
                        </div>
                      </div>
                      <div className="mt-3 flex justify-end">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDismiss(error.id);
                            if (expandedErrorId === error.id) {
                              setExpandedErrorId(null);
                            }
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-300 hover:text-white hover:bg-red-900/50 rounded transition-colors"
                        >
                          <X className="h-4 w-4" />
                          Dismiss
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
