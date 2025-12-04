import { useState, useEffect } from "react";
import { apiClient, EvaluationRun } from "@/lib/api";

export function useAgentEvaluations(agentId: string | undefined) {
	const [evaluations, setEvaluations] = useState<EvaluationRun[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchEvaluations = async () => {
		if (!agentId) {
			setLoading(false);
			return;
		}

		try {
			setLoading(true);
			setError(null);

			// Fetch evaluations filtered by agent_id on the backend
			const agentEvaluations = await apiClient.getEvaluations(0, 100, agentId);

			// Backend already returns sorted by created_at DESC, but sort again to be safe
			agentEvaluations.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

			setEvaluations(agentEvaluations);
		} catch (err) {
			console.error("Failed to fetch agent evaluations:", err);
			setError(err instanceof Error ? err.message : "Failed to fetch evaluations");
			setEvaluations([]);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchEvaluations();
	}, [agentId]);

	return {
		evaluations,
		loading,
		error,
		refetch: fetchEvaluations,
	};
}
