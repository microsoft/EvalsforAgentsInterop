import { useState, useEffect, useCallback } from "react";
import { apiClient, EvaluationRun, BackendTestCase } from "@/lib/api";

export function useEvaluation(evaluationId: string | undefined, enablePolling = false) {
	const [evaluation, setEvaluation] = useState<EvaluationRun | null>(null);
	const [testCases, setTestCases] = useState<BackendTestCase[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchEvaluation = useCallback(async () => {
		if (!evaluationId) {
			setLoading(false);
			return;
		}

		try {
			setError(null);
			const data = await apiClient.getEvaluation(evaluationId);
			setEvaluation(data);

			// Fetch test cases from the dataset to get names
			if (data.dataset_id) {
				try {
					const testCaseData = await apiClient.getTestCases(data.dataset_id);
					setTestCases(testCaseData);
				} catch (testCaseError) {
					console.warn("Failed to fetch test cases for names:", testCaseError);
					// Don't fail the whole operation if test cases can't be loaded
					setTestCases([]);
				}
			}

			// Stop loading once we have data
			setLoading(false);
		} catch (err) {
			console.error("Failed to fetch evaluation:", err);
			setError(err instanceof Error ? err.message : "Failed to fetch evaluation");
			setEvaluation(null);
			setTestCases([]);
			setLoading(false);
		}
	}, [evaluationId]);

	useEffect(() => {
		fetchEvaluation();
	}, [fetchEvaluation]);

	// Polling for live updates when evaluation is running
	useEffect(() => {
		if (!enablePolling || !evaluation || evaluation.status === "completed" || evaluation.status === "failed" || evaluation.status === "cancelled") {
			return;
		}

		const interval = setInterval(() => {
			fetchEvaluation();
		}, 3000); // Poll every 3 seconds

		return () => clearInterval(interval);
	}, [enablePolling, evaluation, fetchEvaluation]);

	const refetch = () => {
		setLoading(true);
		fetchEvaluation();
	};

	return {
		evaluation,
		testCases,
		loading,
		error,
		refetch,
	};
}
