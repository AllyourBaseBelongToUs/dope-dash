// Shared types between frontend and backend

export interface Agent {
  id: string;
  name: string;
  type: "ralph" | "claude" | "cursor" | "terminal";
  status: "idle" | "running" | "paused" | "error" | "stopped";
  project: string;
  currentTask?: string;
  quotaUsed: number;
  quotaLimit: number;
  rateLimitStatus: "ok" | "warning" | "limited";
  lastHeartbeat?: string;
  createdAt: string;
  pid?: number;
  workingDir?: string;
  command?: string;
  tmuxSession?: string;
  capabilities?: string[];
}

export interface AgentMessage {
  id: string;
  agentId: string;
  type: "user" | "assistant" | "system" | "error";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface AgentPool {
  id: string;
  name: string;
  agents: Agent[];
  maxConcurrent: number;
  state: "stopped" | "starting" | "running" | "stopping" | "error";
}

export interface QuotaAlert {
  id: string;
  agentId: string;
  agentName: string;
  type: "warning" | "critical";
  message: string;
  quotaUsed: number;
  quotaLimit: number;
  timestamp: string;
  acknowledged: boolean;
}

// FIXED: Updated to match frontend CommandHistoryEntry structure
// This is the shared type that both frontend and backend should use
export interface SharedCommandHistoryEntry {
  id: string;
  projectId?: string;
  sessionId?: string;
  command: string;
  status: 'pending' | 'sent' | 'acknowledged' | 'completed' | 'failed' | 'timeout';
  result?: string;
  errorMessage?: string;
  exitCode?: number;
  durationMs?: number;
  isFavorite: boolean;
  templateName?: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

// Legacy command entry type for backward compatibility
// @deprecated Use SharedCommandHistoryEntry instead
export interface CommandHistoryEntry {
  id: string;
  agentId: string;
  command: string;
  args: string[];
  timestamp: string;
  duration?: number;
  exitCode?: number;
}
