/**
 * Configurable color system for agents and status indicators.
 *
 * Colors can be customized in two ways:
 * 1. Edit the arrays below to change the palette
 * 2. Override via CSS variables in globals.css for theming
 */

// CSS variable names for theming
const CSS_VARS = {
  // Status colors
  statusAvailable: '--status-available',
  statusBusy: '--status-busy',
  statusOffline: '--status-offline',
  statusMaintenance: '--status-maintenance',
  statusDraining: '--status-draining',

  // Agent type colors
  typeRalph: '--agent-ralph',
  typeClaude: '--agent-claude',
  typeCursor: '--agent-cursor',
  typeTerminal: '--agent-terminal',
  typeCrawler: '--agent-crawler',
  typeAnalyzer: '--agent-analyzer',
  typeReporter: '--agent-reporter',
  typeTester: '--agent-tester',
  typeCustom: '--agent-custom',

  // Utilization thresholds
  utilHigh: '--util-high',    // >= 80%
  utilMedium: '--util-medium', // >= 60%
  utilLow: '--util-low',       // < 60%
};

// Default color palettes (used when CSS variables not defined)
export const AGENT_LINK_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#ec4899', // pink
];

export const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  available: { bg: '#22c55e20', text: '#22c55e', border: '#22c55e40' },
  busy: { bg: '#3b82f620', text: '#3b82f6', border: '#3b82f640' },
  offline: { bg: '#ef444420', text: '#ef4444', border: '#ef444440' },
  maintenance: { bg: '#eab30820', text: '#eab308', border: '#eab30840' },
  draining: { bg: '#f9731620', text: '#f97316', border: '#f9731640' },
};

export const AGENT_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  ralph: { bg: '#8b5cf620', text: '#8b5cf6' },
  claude: { bg: '#f9731620', text: '#f97316' },
  cursor: { bg: '#3b82f620', text: '#3b82f6' },
  terminal: { bg: '#6b728020', text: '#6b7280' },
  crawler: { bg: '#22c55e20', text: '#22c55e' },
  analyzer: { bg: '#06b6d420', text: '#06b6d4' },
  reporter: { bg: '#ec489920', text: '#ec4899' },
  tester: { bg: '#eab30820', text: '#eab308' },
  custom: { bg: '#6366f120', text: '#6366f1' },
};

export const UTILIZATION_COLORS = {
  high: '#ef4444',   // >= 80%
  medium: '#eab308', // >= 60%
  low: '#22c55e',    // < 60%
} as const;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get a deterministic link color for an agent based on their ID.
 */
export function getAgentColor(agentId: string): string {
  const hash = agentId.split('').reduce((acc, char) => {
    return acc + char.charCodeAt(0);
  }, 0);
  return AGENT_LINK_COLORS[hash % AGENT_LINK_COLORS.length];
}

/**
 * Get CSS styles for color-coded agent-project linking.
 */
export function getLinkStyles(agentId: string): {
  borderColor: string;
  bgColor: string;
} {
  const color = getAgentColor(agentId);
  return {
    borderColor: color,
    bgColor: `${color}10`,
  };
}

/**
 * Get a contrasting text color for the given agent color.
 */
export function getTextColor(agentId: string): string {
  const color = getAgentColor(agentId);
  const r = parseInt(color.slice(1, 3), 16);
  const g = parseInt(color.slice(3, 5), 16);
  const b = parseInt(color.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#000000' : '#ffffff';
}

/**
 * Get status color classes (Tailwind-compatible).
 * Returns bg opacity, text color, and border classes.
 */
export function getStatusColorClasses(status: string): string {
  const colors = STATUS_COLORS[status as keyof typeof STATUS_COLORS];
  if (!colors) return 'bg-muted text-muted-foreground';

  // Use inline styles for custom colors, but return a base class
  return 'bg-opacity-10';
}

/**
 * Get status color as inline styles (for full customization).
 */
export function getStatusStyles(status: string): React.CSSProperties {
  const colors = STATUS_COLORS[status as keyof typeof STATUS_COLORS];
  if (!colors) return {};

  return {
    backgroundColor: colors.bg,
    color: colors.text,
    borderColor: colors.border,
  };
}

/**
 * Get agent type color as inline styles.
 */
export function getAgentTypeStyles(type: string): React.CSSProperties {
  const colors = AGENT_TYPE_COLORS[type] || AGENT_TYPE_COLORS.custom;
  return {
    backgroundColor: colors.bg,
    color: colors.text,
  };
}

/**
 * Get utilization color based on percentage.
 */
export function getUtilizationColor(percent: number): string {
  if (percent >= 80) return UTILIZATION_COLORS.high;
  if (percent >= 60) return UTILIZATION_COLORS.medium;
  return UTILIZATION_COLORS.low;
}

/**
 * Get utilization color as inline style.
 */
export function getUtilizationStyle(percent: number): React.CSSProperties {
  return {
    backgroundColor: getUtilizationColor(percent),
  };
}

// ============================================================================
// Configuration (for runtime customization)
// ============================================================================

/**
 * Override default agent type colors at runtime.
 * Useful for user preferences or theme switching.
 */
export function setAgentTypeColor(type: string, bg: string, text: string): void {
  AGENT_TYPE_COLORS[type] = { bg, text };
}

/**
 * Override default status colors at runtime.
 */
export function setStatusColor(
  status: string,
  bg: string,
  text: string,
  border: string
): void {
  STATUS_COLORS[status] = { bg, text, border };
}

/**
 * Override the link color palette at runtime.
 */
export function setLinkColors(colors: string[]): void {
  AGENT_LINK_COLORS.length = 0;
  AGENT_LINK_COLORS.push(...colors);
}
