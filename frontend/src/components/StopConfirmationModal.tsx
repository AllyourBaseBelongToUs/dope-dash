'use client';

import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle, X } from 'lucide-react';

interface StopConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  projectName?: string;
}

export function StopConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  projectName,
}: StopConfirmationModalProps) {
  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-6 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="bg-red-950/30 border border-red-900/50 rounded-full p-3">
                <AlertTriangle className="h-6 w-6 text-red-500" />
              </div>
            </div>
            <div className="flex-1">
              <Dialog.Title className="text-lg font-semibold text-foreground mb-2">
                Stop Agent Session?
              </Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground">
                {projectName ? (
                  <>
                    Are you sure you want to stop the agent session for <span className="font-medium text-foreground">{projectName}</span>?
                    This action will terminate the current spec execution and cannot be undone.
                  </>
                ) : (
                  <>
                    Are you sure you want to stop this agent session? This action will terminate
                    the current spec execution and cannot be undone.
                  </>
                )}
              </Dialog.Description>

              <div className="mt-6 flex items-center justify-end gap-3">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="px-4 py-2 text-sm font-medium text-foreground border border-border rounded-md hover:bg-muted transition-colors"
                  >
                    Cancel
                  </button>
                </Dialog.Close>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors"
                >
                  Stop Session
                </button>
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
