import { useState, useEffect, useCallback } from "react";
import { apiClient, EvaluationRun } from "@/lib/api";

export function useEvaluations() {
	const [evaluations, setEvaluations] = useState<EvaluationRun[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchEvaluations = useCallback(async () => {
		try {
			setError(null);
			const data = await apiClient.getEvaluations();
			setEvaluations(data);
		} catch (err) {
			console.error("Failed to fetch evaluations:", err);
			setError(err instanceof Error ? err.message : "Failed to fetch evaluations");
			setEvaluations([]);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchEvaluations();
	}, [fetchEvaluations]);

	const refetch = () => {
		setLoading(true);
		fetchEvaluations();
	};

	return { evaluations, loading, error, refetch };
}