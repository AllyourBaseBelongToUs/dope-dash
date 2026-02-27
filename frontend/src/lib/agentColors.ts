// Color palette for agent-project linking
const LINK_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#ec4899', // pink
];

/**
 * Get a deterministic color for an agent based on their ID.
 * Uses a simple hash function to ensure the same agent always gets the same color.
 */
export function getAgentColor(agentId: string): string {
  const hash = agentId.split('').reduce((acc, char) => {
    return acc + char.charCodeAt(0);
  }, 0);
  return LINK_COLORS[hash % LINK_COLORS.length];
}

/**
 * Get CSS styles for color-coded agent-project linking.
 * Returns border color and background color (10% opacity).
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
 * Returns black for light colors, white for dark colors.
 */
export function getTextColor(agentId: string): string {
  const color = getAgentColor(agentId);
  // Convert hex to RGB
  const r = parseInt(color.slice(1, 3), 16);
  const g = parseInt(color.slice(3, 5), 16);
  const b = parseInt(color.slice(5, 7), 16);
  // Calculate luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#000000' : '#ffffff';
}
