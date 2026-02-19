import { create } from 'zustand';
import type { Session, Event, WebSocketMessage, ConnectionStatus, SpecProgress, DashboardCommandEntry, ErrorEvent } from '@/types';
import { useNotificationStore } from '@/store/notificationStore';

interface DashboardStore {
  sessions: Session[];
  events: Event[];
  connectionStatus: ConnectionStatus;
  activeSessionId: string | null;
  error: string | null;
  errors: ErrorEvent[];
  dismissedErrors: Set<string>;

  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
  processMessage: (message: WebSocketMessage) => void;
  addEvent: (event: Event) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  createSession: (session: Session) => void;
  setActiveSession: (sessionId: string | null) => void;
  clearEvents: () => void;
  clearSessions: () => void;

  // Command actions
  addCommandToHistory: (sessionId: string, command: DashboardCommandEntry) => void;
  updateCommandInHistory: (sessionId: string, commandId: string, updates: Partial<DashboardCommandEntry>) => void;
  getLatestCommandStatus: (sessionId: string) => DashboardCommandEntry | null;

  // Error actions
  addError: (error: ErrorEvent) => void;
  dismissError: (errorId: string) => void;
  getSessionErrors: (sessionId: string) => ErrorEvent[];
  getActiveErrors: () => ErrorEvent[];
  clearDismissedErrors: () => void;
}

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  sessions: [],
  events: [],
  connectionStatus: 'disconnected',
  activeSessionId: null,
  error: null,
  errors: [],
  dismissedErrors: new Set<string>(),

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  setError: (error) => set({ error }),

  clearEvents: () => set({ events: [] }),

  clearSessions: () => set({ sessions: [] }),

  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),

  addEvent: (event) => set((state) => ({
    events: [event, ...state.events].slice(0, 1000), // Keep last 1000 events
  })),

  createSession: (session) => set((state) => {
    // Check if session already exists
    const existingIndex = state.sessions.findIndex(s => s.id === session.id);
    if (existingIndex >= 0) {
      return state; // Session already exists
    }
    return {
      sessions: [...state.sessions, session],
      activeSessionId: state.activeSessionId || session.id,
    };
  }),

  updateSession: (sessionId, updates) => set((state) => ({
    sessions: state.sessions.map((session) =>
      session.id === sessionId ? { ...session, ...updates } : session
    ),
  })),

  addCommandToHistory: (sessionId, command) => set((state) => ({
    sessions: state.sessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            commandHistory: [
              ...(session.commandHistory || []),
              command
            ].slice(-10), // Keep last 10 commands
          }
        : session
    ),
  })),

  updateCommandInHistory: (sessionId, commandId, updates) => set((state) => ({
    sessions: state.sessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            commandHistory: (session.commandHistory || []).map((cmd) =>
              cmd.commandId === commandId ? { ...cmd, ...updates } : cmd
            ),
          }
        : session
    ),
  })),

  getLatestCommandStatus: (sessionId) => {
    const state = get();
    const session = state.sessions.find(s => s.id === sessionId);
    if (!session || !session.commandHistory || session.commandHistory.length === 0) {
      return null;
    }
    return session.commandHistory[session.commandHistory.length - 1];
  },

  // Error actions
  addError: (error) => set((state) => ({
    errors: [error, ...state.errors].slice(0, 500), // Keep last 500 errors
  })),

  dismissError: (errorId) => set((state) => {
    const newDismissed = new Set(state.dismissedErrors);
    newDismissed.add(errorId);
    return { dismissedErrors: newDismissed };
  }),

  getSessionErrors: (sessionId) => {
    const state = get();
    return state.errors.filter(e => e.sessionId === sessionId && !state.dismissedErrors.has(e.id));
  },

  getActiveErrors: () => {
    const state = get();
    return state.errors.filter(e => !state.dismissedErrors.has(e.id));
  },

  clearDismissedErrors: () => set({ dismissedErrors: new Set<string>() }),

  processMessage: (message) => {
    const { sessions, events } = get();

    // Add event to history
    if (message.id && message.session_id) {
      const newEvent: Event = {
        id: message.id,
        sessionId: message.session_id,
        eventType: (message.event_type || 'progress') as any,
        data: message.data || {},
        createdAt: message.created_at || new Date().toISOString(),
      };
      set((state) => ({
        events: [newEvent, ...state.events].slice(0, 1000),
      }));
    }

    // Find or create session
    let session = sessions.find(s => s.id === message.session_id);

    if (!session && message.session_id) {
      // Create new session from session_start event
      if (message.event_type === 'session_start') {
        const now = new Date().toISOString();
        const newSession: Session = {
          id: message.session_id,
          agentType: ((message.data?.agent_type as string) || 'ralph') as any,
          projectName: (message.data?.project_name as string) || 'unknown',
          status: 'running',
          startedAt: message.created_at || now,
          createdAt: now,
          updatedAt: now,
          metadata: (message.data as Record<string, unknown>) || {},
          specs: [],
          completedSpecs: 0,
          totalSpecs: 0,
          progress: 0,
          lastActivity: message.created_at || now,
          agentStatus: 'running',
          commandHistory: [],
        };
        set((state) => ({
          sessions: [...state.sessions, newSession],
          activeSessionId: state.activeSessionId || newSession.id,
        }));
        session = newSession;
      }
    }

    if (!session) return;

    // Update session based on event type
    switch (message.event_type) {
      case 'spec_start': {
        const specName = message.data?.spec_name as string;
        if (!specName) break;

        const existingSpecs = session.specs || [];
        const specExists = existingSpecs.some(s => s.specName === specName);

        let newSpecs: SpecProgress[];
        if (specExists) {
          newSpecs = existingSpecs.map(s =>
            s.specName === specName
              ? { ...s, status: 'running', startedAt: message.created_at }
              : s
          );
        } else {
          newSpecs = [...existingSpecs, {
            specName,
            status: 'running',
            startedAt: message.created_at,
          }];
        }

        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === session.id
              ? {
                  ...s,
                  specs: newSpecs,
                  currentSpec: specName,
                  lastActivity: message.created_at || new Date().toISOString(),
                }
              : s
          ),
        }));
        break;
      }

      case 'spec_complete': {
        const specName = message.data?.spec_name as string;
        const duration = message.data?.duration as number | undefined;

        if (!specName) break;

        const newSpecs = session.specs.map(s =>
          s.specName === specName
            ? {
                ...s,
                status: 'completed' as const,
                completedAt: message.created_at,
                duration,
              }
            : s
        );

        const completedCount = newSpecs.filter(s => s.status === 'completed').length;
        const totalCount = newSpecs.length;
        const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === session.id
              ? {
                  ...s,
                  specs: newSpecs,
                  completedSpecs: completedCount,
                  totalSpecs: totalCount,
                  progress,
                  lastActivity: message.created_at || new Date().toISOString(),
                }
              : s
          ),
        }));

        // Trigger notification
        useNotificationStore.getState().addNotification(
          'spec_complete',
          `Spec Completed: ${specName}`,
          `Spec "${specName}" has been completed successfully.`,
          session.id
        );
        break;
      }

      case 'spec_fail':
      case 'error': {
        const errorMessage = message.data?.error as string || message.data?.message as string;
        const stackTrace = message.data?.stack_trace as string | undefined;

        // Track error in errors list
        if (message.id && message.session_id) {
          const errorEvent: ErrorEvent = {
            id: message.id,
            sessionId: message.session_id,
            eventType: message.event_type as 'error' | 'spec_fail',
            message: errorMessage || 'Unknown error',
            stackTrace,
            data: message.data || {},
            createdAt: message.created_at || new Date().toISOString(),
          };
          get().addError(errorEvent);
        }

        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === session.id
              ? {
                  ...s,
                  error: errorMessage || 'Unknown error',
                  errorCount: (s.errorCount || 0) + 1,
                  lastActivity: message.created_at || new Date().toISOString(),
                }
              : s
          ),
        }));

        // Trigger notification
        useNotificationStore.getState().addNotification(
          'error',
          `Error in ${session.projectName}`,
          errorMessage || 'An unknown error occurred',
          session.id
        );
        break;
      }

      case 'session_end': {
        const status = message.data?.status as string | undefined;
        const finalStatus = status === 'failed' ? 'failed' : 'completed';

        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === session.id
              ? {
                  ...s,
                  status: finalStatus,
                  endedAt: message.created_at || new Date().toISOString(),
                  lastActivity: message.created_at || new Date().toISOString(),
                }
              : s
          ),
        }));

        // Trigger notification for session completion
        useNotificationStore.getState().addNotification(
          'agent_stopped',
          `Session ${finalStatus === 'completed' ? 'Completed' : 'Failed'}`,
          `${session.projectName} has ${finalStatus}.`,
          session.id
        );
        break;
      }

      case 'progress': {
        const progressValue = message.data?.progress as number | undefined;
        if (progressValue !== undefined) {
          set((state) => ({
            sessions: state.sessions.map(s =>
              s.id === session.id
                ? {
                    ...s,
                    progress: progressValue,
                    lastActivity: message.created_at || new Date().toISOString(),
                  }
                : s
            ),
          }));
        }
        break;
      }

      case 'atom_start':
      case 'atom_complete':
      case 'iteration_start':
      case 'iteration_complete':
      case 'subtask_start':
      case 'subtask_complete': {
        // Just update last activity
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === session.id
              ? {
                  ...s,
                  lastActivity: message.created_at || new Date().toISOString(),
                }
              : s
          ),
        }));
        break;
      }
    }
  },
}));
