// Control API client for sending commands to agents

export type ControlCommand = 'pause' | 'resume' | 'skip' | 'stop';

export interface CommandRequest {
  command: ControlCommand;
  timeout_seconds?: number;
  metadata?: Record<string, unknown>;
}

export interface CommandResponse {
  command_id: string;
  status: 'pending' | 'acknowledged' | 'completed' | 'failed' | 'timeout';
  created_at: string;
  timeout_at: string;
  error?: string;
}

export interface SessionStatusResponse {
  is_online: boolean;
  pending_commands: string[];
  last_command?: {
    command_id: string;
    command: ControlCommand;
    status: string;
    created_at: string;
  };
}

const CONTROL_API_URL = process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8002';

/**
 * Send a command to a session
 */
export async function sendCommand(
  sessionId: string,
  command: ControlCommand,
  sessionToken?: string
): Promise<CommandResponse> {
  const response = await fetch(`${CONTROL_API_URL}/api/control/${sessionId}/command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(sessionToken && { 'X-Session-Token': sessionToken }),
    },
    body: JSON.stringify({
      command,
      timeout_seconds: 60,
      metadata: {},
    } satisfies CommandRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Failed to send ${command} command`);
  }

  return response.json() as Promise<CommandResponse>;
}

/**
 * Get the current status of a session
 */
export async function getSessionStatus(
  sessionId: string,
  sessionToken?: string
): Promise<SessionStatusResponse> {
  const response = await fetch(`${CONTROL_API_URL}/api/control/${sessionId}/status`, {
    method: 'GET',
    headers: {
      ...(sessionToken && { 'X-Session-Token': sessionToken }),
    },
  });

  if (!response.ok) {
    throw new Error('Failed to get session status');
  }

  return response.json() as Promise<SessionStatusResponse>;
}

/**
 * Check if a session is online and can receive commands
 */
export async function isSessionOnline(
  sessionId: string,
  sessionToken?: string
): Promise<boolean> {
  try {
    const status = await getSessionStatus(sessionId, sessionToken);
    return status.is_online;
  } catch {
    return false;
  }
}
