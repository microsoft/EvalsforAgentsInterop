// Re-export types from api for convenience
export type { BackendDataset as Dataset, BackendTestCase as TestCase } from "./api";

export interface Agent {
	id: string;
	name: string;
	description: string;
	model: string;
	agent_invocation_url: string;
	createdAt: string;
}

export interface TestCaseResult {
	testCaseId: string;
	scores: {
		groundedness: number;
		toolEfficiency: number;
		accuracy: number;
		relevance: number;
	};
	passed: boolean;
	feedback?: string;
}

export interface EvaluationResult {
	id: string;
	datasetId: string;
	datasetName: string;
	agentId: string;
	agentName: string;
	testCaseResults: TestCaseResult[];
	averageScores: {
		groundedness: number;
		toolEfficiency: number;
		accuracy: number;
		relevance: number;
		overall: number;
	};
	createdAt: string;
}

export interface EvaluationRun {
	id: string;
	name: string;
	datasets: string[];
	agents: string[];
	results: EvaluationResult[];
	status: "pending" | "running" | "completed" | "failed";
	createdAt: string;
	completedAt?: string;
}

export type RubricType = "groundedness" | "toolEfficiency" | "accuracy" | "relevance" | "overall";
