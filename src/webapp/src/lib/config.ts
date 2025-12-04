/**
 * Application configuration
 * 
 * This module provides access to environment variables and feature flags
 * used throughout the application.
 */

/**
 * Flight configuration for UI features
 * 
 * This object contains feature flags that control the visibility and behavior
 * of various UI elements. These are purely UX controls and do not affect
 * backend evaluator behavior.
 */
export const flightConfigurationForUI = {
  /**
   * Feature flag to control rubrics UX visibility
   * 
   * When enabled, rubrics are displayed in:
   * - Test case detail pages (rubric cards with Azure Foundry ID, threshold, payload)
   * - Test case result pages (rubric summary information)
   * - Tool argument expectations (rubric details within tool cards)
   * 
   * When disabled (default), all rubric-related UI elements are hidden.
   * Note: This is purely a UX control - it does not affect evaluator behavior.
   * 
   * @default false
   */
  enableRubricsUX: import.meta.env.VITE_ENABLE_RUBRICS_UX === 'true',
} as const;

/**
 * API base URL for backend communication
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
