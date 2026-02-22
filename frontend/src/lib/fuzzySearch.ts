/**
 * Fuzzy search utilities using Fuse.js
 *
 * Provides configurable fuzzy search for agents, projects, and other entities.
 */
import Fuse, { IFuseOptions } from 'fuse.js';
import type { AgentPoolAgent, Project } from '@/types';

// Searchable wrapper type for agents with original reference
export interface SearchableAgent extends Omit<AgentPoolAgent, never> {
  _original: AgentPoolAgent;
}

// Searchable wrapper type for projects with original reference
export interface SearchableProject extends Omit<Project, never> {
  _original: Project;
}

// Agent search configuration
const agentSearchKeys: ({ name: keyof AgentPoolAgent; weight: number })[] = [
  { name: 'agentId', weight: 0.4 },
  { name: 'agentType', weight: 0.3 },
  { name: 'capabilities', weight: 0.2 },
  { name: 'workingDir', weight: 0.1 },
];

// Project search configuration
const projectSearchKeys: ({ name: keyof Project; weight: number })[] = [
  { name: 'name', weight: 0.5 },
  { name: 'description', weight: 0.3 },
  { name: 'status', weight: 0.2 },
];

/**
 * Create a Fuse.js search instance for agents
 */
export function createAgentSearch(agents: AgentPoolAgent[]): Fuse<AgentPoolAgent> {
  const options: IFuseOptions<AgentPoolAgent> = {
    keys: agentSearchKeys as IFuseOptions<AgentPoolAgent>['keys'],
    threshold: 0.3,
    includeScore: true,
    findAllMatches: true,
    ignoreLocation: true,
    minMatchCharLength: 2,
  };
  return new Fuse(agents, options);
}

/**
 * Create a Fuse.js search instance for projects
 */
export function createProjectSearch(projects: Project[]): Fuse<Project> {
  const options: IFuseOptions<Project> = {
    keys: projectSearchKeys as IFuseOptions<Project>['keys'],
    threshold: 0.3,
    includeScore: true,
    findAllMatches: true,
    ignoreLocation: true,
    minMatchCharLength: 2,
  };
  return new Fuse(projects, options);
}

/**
 * Search agents with a query string
 * Returns up to `limit` results sorted by relevance
 */
export function searchAgents(
  agents: AgentPoolAgent[],
  query: string,
  limit: number = 10
): AgentPoolAgent[] {
  if (!query.trim()) {
    return agents.slice(0, limit);
  }

  const fuse = createAgentSearch(agents);
  const results = fuse.search(query, { limit });

  return results.map(result => result.item);
}

/**
 * Search projects with a query string
 * Returns up to `limit` results sorted by relevance
 */
export function searchProjects(
  projects: Project[],
  query: string,
  limit: number = 10
): Project[] {
  if (!query.trim()) {
    return projects.slice(0, limit);
  }

  const fuse = createProjectSearch(projects);
  const results = fuse.search(query, { limit });

  return results.map(result => result.item);
}

/**
 * Filter agents by status and capabilities
 */
export function filterAgents(
  agents: AgentPoolAgent[],
  options: {
    status?: AgentPoolAgent['status'] | 'all';
    capabilities?: string[];
    availableOnly?: boolean;
  }
): AgentPoolAgent[] {
  return agents.filter(agent => {
    // Status filter
    if (options.status && options.status !== 'all' && agent.status !== options.status) {
      return false;
    }

    // Available only filter
    if (options.availableOnly && !agent.isAvailable) {
      return false;
    }

    // Capabilities filter (agent must have ALL requested capabilities)
    if (options.capabilities && options.capabilities.length > 0) {
      const hasAllCapabilities = options.capabilities.every(cap =>
        agent.capabilities.includes(cap)
      );
      if (!hasAllCapabilities) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Get available agent types from a list of agents
 */
export function getAvailableAgentTypes(agents: AgentPoolAgent[]): string[] {
  const types = new Set(agents.map(a => a.agentType));
  return Array.from(types).sort();
}

/**
 * Get all unique capabilities from a list of agents
 */
export function getAllCapabilities(agents: AgentPoolAgent[]): string[] {
  const capabilities = new Set<string>();
  agents.forEach(agent => {
    agent.capabilities.forEach(cap => capabilities.add(cap));
  });
  return Array.from(capabilities).sort();
}
