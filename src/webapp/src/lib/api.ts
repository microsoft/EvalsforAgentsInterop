// API client for the Agent Arena backend
import { API_BASE_URL } from "./config";

// Backend types from the API matching models2.py schema

export interface Rubric {
	id: string;
	name: string;
	azure_foundry_id: string;
	payload: Record<string, any>;
	threshold: number;
}

export interface ArgumentAssertion {
	name: string;
	assertion: string[]; // List of assertion strings
	rubrics: Rubric[];
}

export interface ToolExpectation {
	name: string;
	arguments: ArgumentAssertion[];
}

export interface ResponseQualityAssertion {
	assertion: string;
	rubrics: Rubric[];
}

export interface BackendTestCase {
	id: string;
	dataset_id: string;
	name?: string | null;
	description: string;
	input: string;
	minimal_tool_set: string[];
	tool_expectations: ToolExpectation[];
	expected_response: string;
	response_quality_expectation?: ResponseQualityAssertion | null;
	references_seed: Record<string, any>;
}

export interface Metadata {
	generator_id: string;
	suite_id: string;
	created_at: string;
	version: string;
	schema_hash: string;
}

export interface SeedDataset {
	name: string;
	goal: string;
	input: Record<string, any>;
}

// DatasetResponse from API (without inline test_cases)
export interface DatasetResponse {
	id: string;
	metadata: Metadata;
	seed: SeedDataset;
	test_case_ids: string[];
	created_at: string;
}

// Combined type for frontend use (dataset + test cases)
export interface BackendDataset {
	id: string;
	metadata: Metadata;
	seed: SeedDataset;
	test_case_ids: string[];
	test_cases: BackendTestCase[];
	created_at: string;
}

export interface BackendAgent {
	id: string;
	name: string;
	description: string;
	model: string;
	agent_invocation_url: string;
	createdAt: string;
}

export interface CreateDatasetRequest {
	seed: string;
	metadata?: Record<string, any>;
}

export interface CreateAgentRequest {
	name: string;
	description?: string;
	model?: string;
	agent_invocation_url: string;
}

export interface CreateTestCaseRequest {
	input: string;
	expectedTools: string[];
	evaluationCriteria: string;
}

export type EvaluationRunStatus = "pending" | "running" | "completed" | "failed";

// Structured evaluation result types
export interface AssertionResult {
	passed: boolean;
	llm_judge_output: string;
}

export interface ArgumentAssertionResult {
	name_of_argument: string;
	assertions: AssertionResult[];
}

export interface ToolExpectationResult {
	name_of_tool: string;
	arguments: ArgumentAssertionResult[];
}

export interface ExpectedToolResult {
	name_of_tool: string;
	was_called: boolean;
}

export interface ResponseQualityResult {
	passed: boolean;
	llm_judge_output: string;
}

export interface TestCaseResult {
	testcase_id: string;
	passed: boolean;
	response_from_agent: string;
	expected_tools: ExpectedToolResult[];
	tool_expectations: ToolExpectationResult[];
	response_quality_assertion?: ResponseQualityResult;
	actual_tool_calls: Array<{
		name: string;
		arguments: Array<{ name: string; value: any }>;
		response?: any;  // MCP tool response
	}>;
	execution_error?: string | null;
}

export interface EvaluationRun {
	id: string;
	name: string;
	dataset_id: string;
	agent_id: string;
	status: EvaluationRunStatus;
	agent_endpoint: string;
	agent_auth_required: boolean;
	timeout_seconds: number;
	total_tests: number;
	completed_tests: number;
	failed_tests: number;
	passed_count: number;
	created_at: string;
	started_at?: string | null;
	completed_at?: string | null;
	test_cases: TestCaseResult[];
}

export interface CreateEvaluationRequest {
	name: string;
	dataset_id: string;
	agent_id: string;
	agent_endpoint: string;
	agent_auth_required?: boolean;
	timeout_seconds?: number;
}

class ApiClient {
	private baseUrl: string;

	constructor(baseUrl: string) {
		this.baseUrl = baseUrl;
	}

	// Datasets (Evaluation Datasets)
	async getRawDatasets(skip = 0, limit = 100): Promise<DatasetResponse[]> {
		try {
			const response = await fetch(`${this.baseUrl}/datasets?skip=${skip}&limit=${limit}`);
			if (!response.ok) {
				const errorText = await response.text();
				console.error("API Error:", response.status, errorText);
				throw new Error(`Failed to fetch datasets: ${response.statusText}`);
			}
			const data = await response.json();
			console.log("Fetched datasets:", data);
			return data;
		} catch (error) {
			console.error("Network error fetching datasets:", error);
			throw error;
		}
	}

	async getRawDataset(datasetId: string): Promise<DatasetResponse> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}`);
		if (!response.ok) {
			throw new Error(`Failed to fetch dataset: ${response.statusText}`);
		}
		return response.json();
	}

	// Combined methods for frontend convenience
	async getDatasets(skip = 0, limit = 100): Promise<BackendDataset[]> {
		const rawDatasets = await this.getRawDatasets(skip, limit);
		// For list view, don't fetch test cases - just use empty array
		// The UI can show count from test_case_ids.length
		const datasets = rawDatasets.map((dataset) => ({
			...dataset,
			test_cases: [], // Empty array for list view - count comes from test_case_ids.length
		}));
		console.log("Datasets with test_case_ids:", datasets);
		return datasets;
	}

	async getDataset(datasetId: string): Promise<BackendDataset> {
		const dataset = await this.getRawDataset(datasetId);
		const testCases = await this.getTestCases(datasetId);
		return {
			...dataset,
			test_cases: testCases,
		};
	}

	async createDataset(data: CreateDatasetRequest): Promise<DatasetResponse> {
		const response = await fetch(`${this.baseUrl}/datasets`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error(`Failed to create dataset: ${response.statusText}`);
		}
		return response.json();
	}

	async deleteDataset(datasetId: string): Promise<void> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}`, {
			method: "DELETE",
		});
		if (!response.ok) {
			throw new Error(`Failed to delete dataset: ${response.statusText}`);
		}
	}

	// Test Cases
	async getTestCases(datasetId: string): Promise<BackendTestCase[]> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/testcases`);
		if (!response.ok) {
			throw new Error(`Failed to fetch test cases: ${response.statusText}`);
		}
		return response.json();
	}

	async getTestCase(datasetId: string, testCaseId: string): Promise<BackendTestCase> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/testcases/${testCaseId}`);
		if (!response.ok) {
			throw new Error(`Failed to fetch test case: ${response.statusText}`);
		}
		return response.json();
	}

	async createTestCase(datasetId: string, data: CreateTestCaseRequest): Promise<BackendTestCase> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/testcases`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error(`Failed to create test case: ${response.statusText}`);
		}
		return response.json();
	}

	async updateTestCase(datasetId: string, testCaseId: string, data: BackendTestCase): Promise<BackendTestCase> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/testcases/${testCaseId}`, {
			method: "PUT",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error(`Failed to update test case: ${response.statusText}`);
		}
		return response.json();
	}

	async deleteTestCase(datasetId: string, testCaseId: string): Promise<void> {
		const response = await fetch(`${this.baseUrl}/datasets/${datasetId}/testcases/${testCaseId}`, {
			method: "DELETE",
		});
		if (!response.ok) {
			throw new Error(`Failed to delete test case: ${response.statusText}`);
		}
	}

	// Agents
	async getAgents(skip = 0, limit = 100): Promise<BackendAgent[]> {
		try {
			const response = await fetch(`${this.baseUrl}/agents?skip=${skip}&limit=${limit}`);
			if (!response.ok) {
				const errorText = await response.text();
				console.error("API Error:", response.status, errorText);
				throw new Error(`Failed to fetch agents: ${response.statusText}`);
			}
			const data = await response.json();
			console.log("Fetched agents:", data);
			return data;
		} catch (error) {
			console.error("Network error fetching agents:", error);
			throw error;
		}
	}

	async getAgent(agentId: string): Promise<BackendAgent> {
		const response = await fetch(`${this.baseUrl}/agents/${agentId}`);
		if (!response.ok) {
			throw new Error(`Failed to fetch agent: ${response.statusText}`);
		}
		return response.json();
	}

	async createAgent(data: CreateAgentRequest): Promise<BackendAgent> {
		const response = await fetch(`${this.baseUrl}/agents`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error(`Failed to create agent: ${response.statusText}`);
		}
		return response.json();
	}

	async updateAgent(agentId: string, data: CreateAgentRequest): Promise<BackendAgent> {
		const response = await fetch(`${this.baseUrl}/agents/${agentId}`, {
			method: "PUT",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error(`Failed to update agent: ${response.statusText}`);
		}
		return response.json();
	}

	async deleteAgent(agentId: string): Promise<void> {
		const response = await fetch(`${this.baseUrl}/agents/${agentId}`, {
			method: "DELETE",
		});
		if (!response.ok) {
			throw new Error(`Failed to delete agent: ${response.statusText}`);
		}
	}

	// Evaluations
	async createEvaluation(data: {
		name: string;
		dataset_id: string;
		agent_id: string;
		agent_endpoint: string;
		agent_auth_required?: boolean;
		timeout_seconds?: number;
	}): Promise<EvaluationRun> {
		const response = await fetch(`${this.baseUrl}/evaluations`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(`Failed to create evaluation: ${response.statusText} - ${errorText}`);
		}
		return response.json();
	}

	async getEvaluations(skip = 0, limit = 100, agentId?: string): Promise<EvaluationRun[]> {
		const params = new URLSearchParams({
			skip: skip.toString(),
			limit: limit.toString(),
		});
		if (agentId) {
			params.append("agent_id", agentId);
		}
		const response = await fetch(`${this.baseUrl}/evaluations?${params}`);
		if (!response.ok) {
			throw new Error(`Failed to fetch evaluations: ${response.statusText}`);
		}
		return response.json();
	}

	async getEvaluation(evaluationId: string): Promise<EvaluationRun> {
		const response = await fetch(`${this.baseUrl}/evaluations/${evaluationId}`);
		if (!response.ok) {
			throw new Error(`Failed to fetch evaluation: ${response.statusText}`);
		}
		return response.json();
	}

	async deleteEvaluation(evaluationId: string): Promise<void> {
		const response = await fetch(`${this.baseUrl}/evaluations/${evaluationId}`, {
			method: "DELETE",
		});
		if (!response.ok) {
			throw new Error(`Failed to delete evaluation: ${response.statusText}`);
		}
	}
}

export const apiClient = new ApiClient(API_BASE_URL);
