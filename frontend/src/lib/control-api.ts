/**
 * Control API client for sending commands to agents.
 *
 * This module provides functions to interact with the Control API server (port 8002)
 * for sending pause, resume, skip, and stop commands to active agent sessions.
 */

const CONTROL_API_BASE_URL = process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8002';

export type CommandType = 'pause' | 'resume' | 'skip' | 'stop';

export interface CommandRequest {
  command: CommandType;
  timeout_seconds?: number;
  metadata?: Record<string, unknown>;
}

export interface CommandResponse {
  command_id: string;
  session_id: string;
  command: CommandType;
  status: 'pending' | 'acknowledged' | 'completed' | 'failed' | 'timeout';
  created_at: string;
  timeout_at: string;
}

export interface SessionStatusResponse {
  session_id: string;
  is_online: boolean;
  pending_commands: number;
  last_command: CommandResponse | null;
}

export class ControlAPIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ControlAPIError';
  }
}

/**
 * Send a control command to an agent session.
 *
 * @param sessionId - The target session ID (UUID string)
 * @param command - The command type to send
 * @param timeoutSeconds - Command timeout in seconds (default: 60)
 * @returns Promise resolving to the command response
 * @throws ControlAPIError if the request fails
 */
export async function sendCommand(
  sessionId: string,
  command: CommandType,
  timeoutSeconds = 60
): Promise<CommandResponse> {
  const url = `${CONTROL_API_BASE_URL}/api/control/${sessionId}/command`;

  const body: CommandRequest = {
    command,
    timeout_seconds: timeoutSeconds,
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // For MVP, we use a placeholder token
        'X-Session-Token': sessionToken(sessionId),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ControlAPIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    const data = (await response.json()) as CommandResponse;
    return data;
  } catch (error) {
    if (error instanceof ControlAPIError) {
      throw error;
    }
    throw new ControlAPIError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

/**
 * Get the status of a session's command queue.
 *
 * @param sessionId - The session ID (UUID string)
 * @returns Promise resolving to session status
 */
export async function getSessionStatus(
  sessionId: string
): Promise<SessionStatusResponse> {
  const url = `${CONTROL_API_BASE_URL}/api/control/${sessionId}/status`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken(sessionId),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ControlAPIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status
      );
    }

    const data = (await response.json()) as SessionStatusResponse;
    return data;
  } catch (error) {
    if (error instanceof ControlAPIError) {
      throw error;
    }
    throw new ControlAPIError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

/**
 * Generate a session token for authentication.
 *
 * For MVP, this is a simple placeholder. In production, this would
 * use a proper authentication mechanism.
 *
 * @param sessionId - The session ID
 * @returns A session token string
 */
function sessionToken(sessionId: string): string {
  // For MVP, use a simple token based on session ID
  return `token-${sessionId.slice(0, 8)}`;
}

/**
 * Debounce function to prevent rapid command sending.
 *
 * @param fn - The function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function debounced(...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}
