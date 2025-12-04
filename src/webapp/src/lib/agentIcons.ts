/**
 * Utility for managing agent icons
 */

// Array of available agent icon file names
const AGENT_ICONS = [
  'agenticon.svg',
  'agenticon2.svg',
  'agenticon3.svg',
  'agenticon4.svg',
  'agenticon5.svg',
  'agenticon6.svg',
  'agenticon7.svg',
];

/**
 * Get a random agent icon for a given agent ID.
 * Uses consistent mapping - same agent ID will always get the same icon.
 * @param agentId - The unique identifier for the agent
 * @returns The path to the agent icon
 */
export function getAgentIcon(agentId: string): string {
  // Validate input
  if (!agentId || typeof agentId !== 'string') {
    console.warn('getAgentIcon called with invalid agentId:', agentId);
    return `/images/${AGENT_ICONS[0]}`;
  }

  // Create a simple hash from the agent ID to ensure consistent icon assignment
  let hash = 0;
  for (let i = 0; i < agentId.length; i++) {
    const char = agentId.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }

  // Use the hash to select an icon
  const iconIndex = Math.abs(hash) % AGENT_ICONS.length;
  const selectedIcon = AGENT_ICONS[iconIndex];
  const fullPath = `/images/${selectedIcon}`;
  
  return fullPath;
}

/**
 * Get all available agent icons
 */
export function getAvailableAgentIcons(): string[] {
  return AGENT_ICONS.map(icon => `/images/${icon}`);
}