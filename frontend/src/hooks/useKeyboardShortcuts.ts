import { useEffect } from 'react';

export type KeyboardShortcutHandler = (event: KeyboardEvent) => void;

export interface KeyboardShortcut {
  key: string;
  handler: KeyboardShortcutHandler;
  description?: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
}

/**
 * Hook for registering keyboard shortcuts
 */
export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  enabled: boolean = true,
  dependencies: unknown[] = []
) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input field
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      for (const shortcut of shortcuts) {
        const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatches = shortcut.ctrlKey === undefined || event.ctrlKey === shortcut.ctrlKey;
        const shiftMatches = shortcut.shiftKey === undefined || event.shiftKey === shortcut.shiftKey;
        const altMatches = shortcut.altKey === undefined || event.altKey === shortcut.altKey;
        const metaMatches = shortcut.metaKey === undefined || event.metaKey === shortcut.metaKey;

        if (keyMatches && ctrlMatches && shiftMatches && altMatches && metaMatches) {
          event.preventDefault();
          shortcut.handler(event);
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, ...dependencies]);
}

/**
 * Hook for agent control keyboard shortcuts
 */
export function useAgentControlShortcuts(
  onPause: () => void,
  onResume: () => void,
  onSkip: () => void,
  onStop: () => void,
  enabled: boolean = true
) {
  useKeyboardShortcuts(
    [
      { key: ' ', handler: onPause, description: 'Pause agent' },
      { key: 'r', handler: onResume, description: 'Resume agent' },
      { key: 's', handler: onSkip, description: 'Skip current task' },
      { key: 'Escape', handler: onStop, description: 'Stop agent' },
    ],
    enabled,
    [onPause, onResume, onSkip, onStop]
  );
}
