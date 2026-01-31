/** Command service for managing custom command history.

Provides methods for sending commands, retrieving history,
managing favorites, and exporting command history.
*/
import type {
  CommandHistoryEntry,
  CommandHistoryListResponse,
  CommandHistoryFilters,
  CommandTemplate,
  SendCommandRequest,
  ReplayCommandRequest,
  ToggleFavoriteRequest,
  CommandStatsSummary,
} from '@/types';

// FIXED: Use consistent API URL from environment or fallback
const API_BASE_URL = process.env.NEXT_PUBLIC_CONTROL_API_URL ||
                      process.env.NEXT_PUBLIC_API_URL ||
                      'http://localhost:8002';

/** Command service class. */
class CommandService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Validate and sanitize project/session ID to prevent path traversal
   */
  private validateId(id: string, idType: 'project' | 'session'): void {
    if (!id || typeof id !== 'string') {
      throw new Error(`Invalid ${idType} ID: must be a non-empty string`);
    }

    // Check for path traversal patterns
    const dangerousPatterns = ['..', '\\', '\0', './', '.\\'];
    const hasDangerousContent = dangerousPatterns.some(pattern => id.includes(pattern));

    if (hasDangerousContent) {
      throw new Error(`Invalid ${idType} ID: potentially dangerous content detected`);
    }

    // Validate format (should be alphanumeric with some safe characters)
    if (!/^[a-zA-Z0-9_-]+$/.test(id)) {
      throw new Error(`Invalid ${idType} ID: must contain only alphanumeric characters, hyphens, and underscores`);
    }
  }

  /**
   * Validate command string to prevent injection attacks
   */
  private validateCommand(command: string): void {
    if (!command || typeof command !== 'string') {
      throw new Error('Invalid command: must be a non-empty string');
    }

    if (command.length > 10000) {
      throw new Error('Invalid command: too long (max 10000 characters)');
    }

    // Check for obviously dangerous patterns
    const dangerousPatterns = [
      '\x00', // null byte
      ';rm ', // command chaining with remove
      '|rm ', // pipe to remove
      '&& rm ', // AND operator with remove
      '|| rm ', // OR operator with remove
    ];

    const hasDangerousContent = dangerousPatterns.some(pattern =>
      command.toLowerCase().includes(pattern.toLowerCase())
    );

    if (hasDangerousContent) {
      throw new Error('Invalid command: potentially dangerous content detected');
    }
  }

  /** Get command history with optional filters. */
  async getCommandHistory(filters: CommandHistoryFilters = {}): Promise<CommandHistoryListResponse> {
    const params = new URLSearchParams();

    if (filters.projectId) params.append('project_id', filters.projectId);
    if (filters.sessionId) params.append('session_id', filters.sessionId);
    if (filters.status) params.append('status', filters.status);
    if (filters.isFavorite !== undefined) params.append('is_favorite', String(filters.isFavorite));
    if (filters.search) params.append('search', filters.search);
    if (filters.limit) params.append('limit', String(filters.limit));
    if (filters.offset !== undefined) params.append('offset', String(filters.offset));

    const response = await fetch(`${this.baseUrl}/api/commands/history?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch command history: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      commands: data.commands.map(this.transformCommandEntry),
      total: data.total,
      limit: data.limit,
      offset: data.offset,
    };
  }

  /** Get command history for a specific project. */
  async getProjectCommandHistory(
    projectId: string,
    filters: Omit<CommandHistoryFilters, 'projectId'> = {}
  ): Promise<CommandHistoryListResponse> {
    // FIXED: Validate projectId to prevent path traversal
    this.validateId(projectId, 'project');

    const params = new URLSearchParams();

    if (filters.status) params.append('status', filters.status);
    if (filters.isFavorite !== undefined) params.append('is_favorite', String(filters.isFavorite));
    if (filters.search) params.append('search', filters.search);
    if (filters.limit) params.append('limit', String(filters.limit));
    if (filters.offset !== undefined) params.append('offset', String(filters.offset));

    const response = await fetch(`${this.baseUrl}/api/commands/projects/${projectId}/history?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch project command history: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      commands: data.commands.map(this.transformCommandEntry),
      total: data.total,
      limit: data.limit,
      offset: data.offset,
    };
  }

  /** Get a single command by ID. */
  async getCommand(commandId: string): Promise<CommandHistoryEntry> {
    const response = await fetch(`${this.baseUrl}/api/commands/history/${commandId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch command: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformCommandEntry(data);
  }

  /** Get recent commands for typeahead. */
  async getRecentCommands(projectId?: string, limit = 20): Promise<string[]> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    params.append('limit', String(limit));

    const response = await fetch(`${this.baseUrl}/api/commands/recent?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch recent commands: ${response.statusText}`);
    }

    const data = await response.json();
    return data.commands || [];
  }

  /** Get favorite commands. */
  async getFavoriteCommands(
    projectId?: string,
    limit = 50,
    offset = 0
  ): Promise<CommandHistoryListResponse> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    params.append('limit', String(limit));
    params.append('offset', String(offset));

    const response = await fetch(`${this.baseUrl}/api/commands/favorites?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch favorite commands: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      commands: data.commands.map(this.transformCommandEntry),
      total: data.total,
      limit: data.limit,
      offset: data.offset,
    };
  }

  /** Get command templates. */
  async getCommandTemplates(): Promise<CommandTemplate[]> {
    const response = await fetch(`${this.baseUrl}/api/commands/templates`);
    if (!response.ok) {
      throw new Error(`Failed to fetch command templates: ${response.statusText}`);
    }

    const data = await response.json();
    return data.templates || [];
  }

  /** Send a custom command. */
  async sendCommand(request: SendCommandRequest): Promise<CommandHistoryEntry> {
    // FIXED: Validate command to prevent injection attacks
    this.validateCommand(request.command);

    // Validate IDs if provided
    if (request.projectId) {
      this.validateId(request.projectId, 'project');
    }
    if (request.sessionId) {
      this.validateId(request.sessionId, 'session');
    }

    const response = await fetch(`${this.baseUrl}/api/commands/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to send command: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformCommandEntry(data);
  }

  /** Replay a previous command. */
  async replayCommand(request: ReplayCommandRequest): Promise<CommandHistoryEntry> {
    const response = await fetch(`${this.baseUrl}/api/commands/replay`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to replay command: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformCommandEntry(data);
  }

  /** Update a command record. */
  async updateCommand(
    commandId: string,
    updates: Partial<Omit<CommandHistoryEntry, 'id' | 'createdAt'>>
  ): Promise<CommandHistoryEntry> {
    const response = await fetch(`${this.baseUrl}/api/commands/history/${commandId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      throw new Error(`Failed to update command: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformCommandEntry(data);
  }

  /** Toggle favorite status of a command. */
  async toggleCommandFavorite(commandId: string, isFavorite: boolean): Promise<CommandHistoryEntry> {
    const response = await fetch(`${this.baseUrl}/api/commands/history/${commandId}/favorite`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ isFavorite }),
    });

    if (!response.ok) {
      throw new Error(`Failed to toggle favorite: ${response.statusText}`);
    }

    const data = await response.json();
    return this.transformCommandEntry(data);
  }

  /** Delete a command record. */
  async deleteCommand(commandId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/commands/history/${commandId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete command: ${response.statusText}`);
    }
  }

  /** Export command history to CSV. */
  async exportCommandHistory(
    projectId: string,
    filters: Omit<CommandHistoryFilters, 'projectId' | 'limit' | 'offset'> = {}
  ): Promise<void> {
    // FIXED: Validate projectId to prevent path traversal attacks
    this.validateId(projectId, 'project');

    const params = new URLSearchParams();

    if (filters.status) params.append('status', filters.status);
    if (filters.isFavorite !== undefined) params.append('is_favorite', String(filters.isFavorite));
    if (filters.search) params.append('search', filters.search);
    params.append('format', 'csv');

    const response = await fetch(`${this.baseUrl}/api/commands/history/${projectId}/export?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`Failed to export command history: ${response.statusText}`);
    }

    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'command_history.csv';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match) {
        // FIXED: Validate filename to prevent path traversal in downloads
        const suggestedFilename = match[1];
        if (suggestedFilename && !suggestedFilename.includes('..') && !suggestedFilename.includes('/')) {
          filename = suggestedFilename;
        }
      }
    }

    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

  /** Get command statistics summary. */
  async getCommandStats(projectId?: string): Promise<CommandStatsSummary> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);

    const response = await fetch(`${this.baseUrl}/api/commands/stats/summary?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch command stats: ${response.statusText}`);
    }

    return await response.json();
  }

  /** Transform command entry from API format to frontend format. */
  private transformCommandEntry(entry: any): CommandHistoryEntry {
    return {
      id: entry.id,
      projectId: entry.projectId,
      sessionId: entry.sessionId,
      command: entry.command,
      status: entry.status,
      result: entry.result,
      errorMessage: entry.errorMessage,
      exitCode: entry.exitCode,
      durationMs: entry.durationMs,
      isFavorite: entry.isFavorite,
      templateName: entry.templateName,
      createdAt: entry.createdAt,
      metadata: entry.metadata,
    };
  }
}

// Singleton instance
let commandServiceInstance: CommandService | null = null;

/** Get the command service singleton instance. */
export function getCommandService(): CommandService {
  if (!commandServiceInstance) {
    commandServiceInstance = new CommandService();
  }
  return commandServiceInstance;
}

export { CommandService };
