import { useState, useEffect } from 'react';
import { Agent } from '@/lib/types';
import { apiClient } from '@/lib/api';

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const backendAgents = await apiClient.getAgents();
      setAgents(backendAgents);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch agents');
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const refetch = () => {
    fetchAgents();
  };

  return {
    agents,
    loading,
    error,
    refetch,
  };
}