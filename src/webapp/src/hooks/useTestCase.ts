import { useState, useEffect, useCallback } from "react";
import { apiClient, BackendTestCase } from "@/lib/api";

export function useTestCase(datasetId: string | undefined, testCaseId: string | undefined) {
	const [testCase, setTestCase] = useState<BackendTestCase | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchTestCase = useCallback(async () => {
		if (!datasetId || !testCaseId) {
			setLoading(false);
			return;
		}

		try {
			setError(null);
			setLoading(true);
			const data = await apiClient.getTestCase(datasetId, testCaseId);
			setTestCase(data);
			setLoading(false);
		} catch (err) {
			console.error("Failed to fetch test case:", err);
			setError(err instanceof Error ? err.message : "Failed to fetch test case");
			setTestCase(null);
			setLoading(false);
		}
	}, [datasetId, testCaseId]);

	useEffect(() => {
		fetchTestCase();
	}, [fetchTestCase]);

	return { testCase, loading, error, refetch: fetchTestCase };
}
