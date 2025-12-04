import { useMemo } from 'react';
import { flightConfigurationForUI } from '@/lib/config';

/**
 * Hook to access rubrics UX configuration
 * 
 * @returns Object containing rubrics configuration
 * @property {boolean} enabled - Whether rubrics UX is enabled
 */
export function useRubricsConfig() {
  return useMemo(() => ({
    enabled: flightConfigurationForUI.enableRubricsUX,
  }), []);
}
