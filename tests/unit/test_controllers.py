"""
Unit Tests for API Controllers/Endpoints

Tests the FastAPI endpoints using mocked Cosmos DB service.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Root endpoint should return API info."""
        response = test_client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "docs" in data
    
    def test_health_endpoint(self, test_client):
        """Health endpoint should return ok status."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"


class TestDatasetEndpoints:
    """Tests for dataset CRUD endpoints."""
    
    def test_create_dataset(self, test_client, sample_dataset_request):
        """POST /api/datasets should create a new dataset."""
        response = test_client.post("/api/datasets", json=sample_dataset_request)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["seed"]["name"] == sample_dataset_request["name"]
        assert data["seed"]["goal"] == sample_dataset_request["goal"]
    
    def test_create_dataset_missing_goal(self, test_client):
        """POST /api/datasets without goal should fail validation."""
        response = test_client.post("/api/datasets", json={"name": "Test"})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_list_datasets_empty(self, test_client):
        """GET /api/datasets with no data should return empty list."""
        response = test_client.get("/api/datasets")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_datasets_with_data(self, test_client, sample_dataset_request):
        """GET /api/datasets should return created datasets."""
        # Create a dataset first
        test_client.post("/api/datasets", json=sample_dataset_request)
        
        response = test_client.get("/api/datasets")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
    
    def test_get_dataset_not_found(self, test_client):
        """GET /api/datasets/{id} for non-existent ID should return 404."""
        response = test_client.get("/api/datasets/non_existent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_dataset_by_id(self, test_client, sample_dataset_request):
        """GET /api/datasets/{id} should return specific dataset."""
        # Create a dataset first
        create_response = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_response.json()["id"]
        
        response = test_client.get(f"/api/datasets/{dataset_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == dataset_id
    
    def test_delete_dataset(self, test_client, sample_dataset_request):
        """DELETE /api/datasets/{id} should remove dataset."""
        # Create a dataset first
        create_response = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_response.json()["id"]
        
        # Delete it
        response = test_client.delete(f"/api/datasets/{dataset_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's gone
        get_response = test_client.get(f"/api/datasets/{dataset_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_dataset_not_found(self, test_client):
        """DELETE /api/datasets/{id} for non-existent ID should return 404."""
        response = test_client.delete("/api/datasets/non_existent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAgentEndpoints:
    """Tests for agent CRUD endpoints."""
    
    def test_create_agent(self, test_client, sample_agent_request):
        """POST /api/agents should create a new agent."""
        response = test_client.post("/api/agents", json=sample_agent_request)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_agent_request["name"]
        assert data["model"] == sample_agent_request["model"]
    
    def test_create_agent_missing_fields(self, test_client):
        """POST /api/agents without required fields should fail."""
        response = test_client.post("/api/agents", json={"name": "Test"})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_list_agents_empty(self, test_client):
        """GET /api/agents with no data should return empty list."""
        response = test_client.get("/api/agents")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_agents_with_data(self, test_client, sample_agent_request):
        """GET /api/agents should return created agents."""
        # Create an agent first
        test_client.post("/api/agents", json=sample_agent_request)
        
        response = test_client.get("/api/agents")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
    
    def test_get_agent_not_found(self, test_client):
        """GET /api/agents/{id} for non-existent ID should return 404."""
        response = test_client.get("/api/agents/non_existent_id")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_agent_by_id(self, test_client, sample_agent_request):
        """GET /api/agents/{id} should return specific agent."""
        # Create an agent first
        create_response = test_client.post("/api/agents", json=sample_agent_request)
        agent_id = create_response.json()["id"]
        
        response = test_client.get(f"/api/agents/{agent_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == agent_id
    
    def test_delete_agent(self, test_client, sample_agent_request):
        """DELETE /api/agents/{id} should remove agent."""
        # Create an agent first
        create_response = test_client.post("/api/agents", json=sample_agent_request)
        agent_id = create_response.json()["id"]
        
        # Delete it
        response = test_client.delete(f"/api/agents/{agent_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's gone
        get_response = test_client.get(f"/api/agents/{agent_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestTestCaseEndpoints:
    """Tests for test case endpoints."""
    
    def test_add_testcase_requires_dataset(self, test_client, sample_testcase_request):
        """POST /api/datasets/{id}/testcases for non-existent dataset should fail."""
        # This tests validation - dataset must exist
        response = test_client.post(
            "/api/datasets/non_existent_id/testcases",
            json=sample_testcase_request
        )
        
        # Should fail because dataset doesn't exist
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""
    
    def test_openapi_json_available(self, test_client):
        """OpenAPI JSON schema should be available."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        
        # Verify key endpoints are documented
        paths = data["paths"]
        assert "/api/datasets" in paths
        assert "/api/agents" in paths
        assert "/api/evaluations" in paths


# =============================================================================
# Tests for API Evaluation Improvements - Endpoint Structure
# =============================================================================
# These tests validate the new endpoints via OpenAPI schema inspection,
# avoiding complex async mocking for the evaluator service.
# =============================================================================


class TestCancelEvaluationEndpoint:
    """Tests for the POST /evaluations/{id}/cancel endpoint."""
    
    def test_cancel_endpoint_exists(self, test_client):
        """Cancel endpoint should be registered in the API."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        
        paths = response.json()["paths"]
        cancel_path = "/api/evaluations/{evaluation_id}/cancel"
        assert cancel_path in paths
        assert "post" in paths[cancel_path]
    
    def test_cancel_endpoint_method(self, test_client):
        """Cancel endpoint should only accept POST method."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        cancel_path = "/api/evaluations/{evaluation_id}/cancel"
        assert "post" in paths[cancel_path]
        assert "get" not in paths[cancel_path]


class TestDeleteEvaluationEndpoint:
    """Tests for DELETE /evaluations/{id} endpoint."""
    
    def test_delete_endpoint_exists(self, test_client):
        """Delete endpoint should be registered in the API."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        
        paths = response.json()["paths"]
        eval_path = "/api/evaluations/{evaluation_id}"
        assert eval_path in paths
        assert "delete" in paths[eval_path]
    
    def test_delete_endpoint_returns_204(self, test_client):
        """Delete endpoint should return 204 on success (per OpenAPI spec)."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        eval_path = "/api/evaluations/{evaluation_id}"
        delete_spec = paths[eval_path]["delete"]
        assert "204" in delete_spec["responses"]


class TestEvaluationEndpointStructure:
    """Tests for evaluation endpoint structure and OpenAPI spec."""
    
    def test_evaluation_list_supports_agent_filter(self, test_client):
        """GET /evaluations should support agent_id query parameter."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        list_path = "/api/evaluations"
        get_spec = paths[list_path]["get"]
        param_names = [p["name"] for p in get_spec.get("parameters", [])]
        assert "agent_id" in param_names
    
    def test_evaluation_list_supports_pagination(self, test_client):
        """GET /evaluations should support skip and limit parameters."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        list_path = "/api/evaluations"
        get_spec = paths[list_path]["get"]
        param_names = [p["name"] for p in get_spec.get("parameters", [])]
        assert "skip" in param_names
        assert "limit" in param_names
    
    def test_evaluation_results_endpoint_exists(self, test_client):
        """GET /evaluations/{id}/results should be registered."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        results_path = "/api/evaluations/{evaluation_id}/results"
        assert results_path in paths
        assert "get" in paths[results_path]
    
    def test_single_result_endpoint_exists(self, test_client):
        """GET /evaluations/{id}/results/{tc_id} should be registered."""
        response = test_client.get("/openapi.json")
        paths = response.json()["paths"]
        
        result_path = "/api/evaluations/{evaluation_id}/results/{testcase_id}"
        assert result_path in paths
        assert "get" in paths[result_path]


class TestEvaluationRunStatusSchema:
    """Tests verifying the EvaluationRun model supports new statuses in API schema."""
    
    def test_cancelled_status_in_schema(self, test_client):
        """EvaluationRunStatus should include 'cancelled' in OpenAPI schema."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRunStatus" in schemas:
            enum_values = schemas["EvaluationRunStatus"]["enum"]
            assert "cancelled" in enum_values
    
    def test_status_history_in_evaluation_run_schema(self, test_client):
        """EvaluationRun schema should include status_history field."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRun" in schemas:
            properties = schemas["EvaluationRun"]["properties"]
            assert "status_history" in properties
    
    def test_timing_fields_in_evaluation_run_schema(self, test_client):
        """EvaluationRun schema should include timing fields."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRun" in schemas:
            properties = schemas["EvaluationRun"]["properties"]
            assert "started_at" in properties
            assert "completed_at" in properties
            assert "created_at" in properties
    
    def test_rate_limit_tracking_in_schema(self, test_client):
        """EvaluationRun schema should include rate limit tracking fields."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRun" in schemas:
            properties = schemas["EvaluationRun"]["properties"]
            assert "total_rate_limit_hits" in properties
            assert "total_retry_wait_seconds" in properties


class TestEvaluationRunCreateSchema:
    """Tests for EvaluationRunCreate request model in API schema."""
    
    def test_create_supports_verbose_logging(self, test_client):
        """EvaluationRunCreate should support verbose_logging option."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRunCreate" in schemas:
            properties = schemas["EvaluationRunCreate"]["properties"]
            assert "verbose_logging" in properties
    
    def test_create_requires_agent_endpoint(self, test_client):
        """EvaluationRunCreate should require agent_endpoint."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "EvaluationRunCreate" in schemas:
            required = schemas["EvaluationRunCreate"].get("required", [])
            assert "agent_endpoint" in required


class TestStatusHistoryEntrySchema:
    """Tests for StatusHistoryEntry model in API schema."""
    
    def test_status_history_entry_schema_exists(self, test_client):
        """StatusHistoryEntry should be defined in OpenAPI schema."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        assert "StatusHistoryEntry" in schemas
    
    def test_status_history_entry_has_rate_limit_fields(self, test_client):
        """StatusHistoryEntry should have rate limit tracking fields."""
        response = test_client.get("/openapi.json")
        schemas = response.json()["components"]["schemas"]
        
        if "StatusHistoryEntry" in schemas:
            properties = schemas["StatusHistoryEntry"]["properties"]
            assert "is_rate_limit" in properties
            assert "retry_attempt" in properties
            assert "wait_seconds" in properties


# =============================================================================
# Functional Controller Tests - Test Case CRUD
# =============================================================================

class TestTestCaseCRUDEndpoints:
    """Functional tests for test case CRUD operations."""
    
    def test_add_testcase_to_dataset(self, test_client, sample_dataset_request, sample_testcase_request):
        """POST /api/datasets/{id}/testcases should add test case to dataset."""
        # First create a dataset
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        assert create_resp.status_code == 201
        dataset_id = create_resp.json()["id"]
        
        # Add a test case
        response = test_client.post(
            f"/api/datasets/{dataset_id}/testcases",
            json=sample_testcase_request
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["dataset_id"] == dataset_id
        assert data["name"] == sample_testcase_request["name"]
    
    def test_list_testcases_for_dataset(self, test_client, sample_dataset_request, sample_testcase_request):
        """GET /api/datasets/{id}/testcases should list all test cases."""
        # Create dataset and test case
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        test_client.post(f"/api/datasets/{dataset_id}/testcases", json=sample_testcase_request)
        
        # List test cases
        response = test_client.get(f"/api/datasets/{dataset_id}/testcases")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["dataset_id"] == dataset_id
    
    def test_get_testcase_by_id(self, test_client, sample_dataset_request, sample_testcase_request):
        """GET /api/datasets/{id}/testcases/{tc_id} should return specific test case."""
        # Create dataset and test case
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        tc_resp = test_client.post(f"/api/datasets/{dataset_id}/testcases", json=sample_testcase_request)
        tc_id = tc_resp.json()["id"]
        
        # Get the test case
        response = test_client.get(f"/api/datasets/{dataset_id}/testcases/{tc_id}")
        
        assert response.status_code == 200
        assert response.json()["id"] == tc_id
        assert response.json()["name"] == sample_testcase_request["name"]
    
    def test_get_testcase_not_found(self, test_client, sample_dataset_request):
        """GET /api/datasets/{id}/testcases/{tc_id} for non-existent should return 404."""
        # Create dataset
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        
        response = test_client.get(f"/api/datasets/{dataset_id}/testcases/non_existent")
        
        assert response.status_code == 404
    
    def test_update_testcase(self, test_client, sample_dataset_request, sample_testcase_request):
        """PUT /api/datasets/{id}/testcases/{tc_id} should update test case."""
        # Create dataset and test case
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        tc_resp = test_client.post(f"/api/datasets/{dataset_id}/testcases", json=sample_testcase_request)
        tc_id = tc_resp.json()["id"]
        
        # Update the test case
        updated_request = {**sample_testcase_request, "name": "Updated Test Case"}
        response = test_client.put(
            f"/api/datasets/{dataset_id}/testcases/{tc_id}",
            json=updated_request
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Test Case"
        assert response.json()["id"] == tc_id  # ID should remain the same
    
    def test_update_testcase_not_found(self, test_client, sample_dataset_request, sample_testcase_request):
        """PUT /api/datasets/{id}/testcases/{tc_id} for non-existent should return 404."""
        # Create dataset
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        
        response = test_client.put(
            f"/api/datasets/{dataset_id}/testcases/non_existent",
            json=sample_testcase_request
        )
        
        assert response.status_code == 404
    
    def test_delete_testcase(self, test_client, sample_dataset_request, sample_testcase_request):
        """DELETE /api/datasets/{id}/testcases/{tc_id} should remove test case."""
        # Create dataset and test case
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        tc_resp = test_client.post(f"/api/datasets/{dataset_id}/testcases", json=sample_testcase_request)
        tc_id = tc_resp.json()["id"]
        
        # Delete it
        response = test_client.delete(f"/api/datasets/{dataset_id}/testcases/{tc_id}")
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = test_client.get(f"/api/datasets/{dataset_id}/testcases/{tc_id}")
        assert get_response.status_code == 404
    
    def test_delete_testcase_not_found(self, test_client, sample_dataset_request):
        """DELETE /api/datasets/{id}/testcases/{tc_id} for non-existent should return 404."""
        # Create dataset
        create_resp = test_client.post("/api/datasets", json=sample_dataset_request)
        dataset_id = create_resp.json()["id"]
        
        response = test_client.delete(f"/api/datasets/{dataset_id}/testcases/non_existent")
        
        assert response.status_code == 404


# =============================================================================
# Functional Controller Tests - Agent Update
# =============================================================================

class TestAgentUpdateEndpoint:
    """Tests for agent update functionality."""
    
    def test_update_agent(self, test_client, sample_agent_request):
        """PUT /api/agents/{id} should update agent."""
        # Create agent
        create_resp = test_client.post("/api/agents", json=sample_agent_request)
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["id"]
        
        # Update it
        updated_request = {**sample_agent_request, "name": "Updated Agent", "model": "gpt-4o-mini"}
        response = test_client.put(f"/api/agents/{agent_id}", json=updated_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Agent"
        assert data["model"] == "gpt-4o-mini"
        assert data["id"] == agent_id  # ID should remain the same
    
    def test_update_agent_not_found(self, test_client, sample_agent_request):
        """PUT /api/agents/{id} for non-existent agent should return 404."""
        response = test_client.put("/api/agents/non_existent", json=sample_agent_request)
        
        assert response.status_code == 404
    
    def test_update_agent_preserves_created_at(self, test_client, sample_agent_request):
        """PUT /api/agents/{id} should preserve the original createdAt timestamp."""
        # Create agent
        create_resp = test_client.post("/api/agents", json=sample_agent_request)
        agent_id = create_resp.json()["id"]
        original_created = create_resp.json()["createdAt"]
        
        # Update it
        updated_request = {**sample_agent_request, "name": "Updated Again"}
        response = test_client.put(f"/api/agents/{agent_id}", json=updated_request)
        
        assert response.status_code == 200
        assert response.json()["createdAt"] == original_created


# =============================================================================
# Functional Controller Tests - Evaluation Endpoints
# =============================================================================

class TestEvaluationFunctionalEndpoints:
    """Functional tests for evaluation endpoints (with mocked evaluator)."""
    
    def test_create_evaluation_success(self, app_with_mocks, sample_evaluation_request):
        """POST /api/evaluations should create evaluation run."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        # Setup mock evaluator to return a proper EvaluationRun
        from src.api.models import EvaluationRun, EvaluationRunStatus
        mock_eval = EvaluationRun(
            id="test-eval-id",
            name=sample_evaluation_request["name"],
            dataset_id=sample_evaluation_request["dataset_id"],
            agent_id=sample_evaluation_request["agent_id"],
            agent_endpoint=sample_evaluation_request["agent_endpoint"],
            status=EvaluationRunStatus.pending
        )
        mock_evaluator.create_evaluation_run = AsyncMock(return_value=mock_eval)
        mock_evaluator.start_evaluation = AsyncMock()
        
        with TestClient(app) as client:
            response = client.post("/api/evaluations", json=sample_evaluation_request)
            
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "test-eval-id"
            assert data["status"] == "pending"
    
    def test_list_evaluations(self, app_with_mocks):
        """GET /api/evaluations should list evaluation runs."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus
        mock_evals = [
            EvaluationRun(
                id="eval-1",
                name="Eval 1",
                dataset_id="ds-1",
                agent_id="agent-1",
                agent_endpoint="http://test",
                status=EvaluationRunStatus.completed
            ),
            EvaluationRun(
                id="eval-2",
                name="Eval 2",
                dataset_id="ds-2",
                agent_id="agent-2",
                agent_endpoint="http://test",
                status=EvaluationRunStatus.running
            )
        ]
        mock_evaluator.list_evaluation_runs = AsyncMock(return_value=mock_evals)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] == "eval-1"
    
    def test_get_evaluation_by_id(self, app_with_mocks):
        """GET /api/evaluations/{id} should return specific evaluation."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus
        mock_eval = EvaluationRun(
            id="eval-123",
            name="Test Eval",
            dataset_id="ds-1",
            agent_id="agent-1",
            agent_endpoint="http://test",
            status=EvaluationRunStatus.completed
        )
        mock_evaluator.get_evaluation_run = AsyncMock(return_value=mock_eval)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations/eval-123")
            
            assert response.status_code == 200
            assert response.json()["id"] == "eval-123"
    
    def test_get_evaluation_not_found(self, app_with_mocks):
        """GET /api/evaluations/{id} for non-existent should return 404."""
        app, mock_db, mock_evaluator = app_with_mocks
        mock_evaluator.get_evaluation_run = AsyncMock(return_value=None)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations/non_existent")
            
            assert response.status_code == 404
    
    def test_get_evaluation_results(self, app_with_mocks):
        """GET /api/evaluations/{id}/results should return test case results."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus, TestCaseResult
        mock_eval = EvaluationRun(
            id="eval-123",
            name="Test Eval",
            dataset_id="ds-1",
            agent_id="agent-1",
            agent_endpoint="http://test",
            status=EvaluationRunStatus.completed,
            test_cases=[
                TestCaseResult(
                    testcase_id="tc-1",
                    passed=True,
                    response_from_agent="Test response 1",
                    expected_tools=[],
                    tool_expectations=[]
                ),
                TestCaseResult(
                    testcase_id="tc-2",
                    passed=False,
                    response_from_agent="Test response 2",
                    expected_tools=[],
                    tool_expectations=[]
                )
            ]
        )
        mock_evaluator.get_evaluation_run = AsyncMock(return_value=mock_eval)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations/eval-123/results")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["testcase_id"] == "tc-1"
    
    def test_get_single_test_result(self, app_with_mocks):
        """GET /api/evaluations/{id}/results/{tc_id} should return specific result."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus, TestCaseResult
        mock_eval = EvaluationRun(
            id="eval-123",
            name="Test Eval",
            dataset_id="ds-1",
            agent_id="agent-1",
            agent_endpoint="http://test",
            status=EvaluationRunStatus.completed,
            test_cases=[
                TestCaseResult(
                    testcase_id="tc-1",
                    passed=True,
                    response_from_agent="Test response 1",
                    expected_tools=[],
                    tool_expectations=[]
                ),
                TestCaseResult(
                    testcase_id="tc-2",
                    passed=False,
                    response_from_agent="Test response 2",
                    expected_tools=[],
                    tool_expectations=[]
                )
            ]
        )
        mock_evaluator.get_evaluation_run = AsyncMock(return_value=mock_eval)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations/eval-123/results/tc-1")
            
            assert response.status_code == 200
            assert response.json()["testcase_id"] == "tc-1"
            assert response.json()["passed"] is True
    
    def test_get_single_test_result_not_found(self, app_with_mocks):
        """GET /api/evaluations/{id}/results/{tc_id} for non-existent tc should return 404."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus
        mock_eval = EvaluationRun(
            id="eval-123",
            name="Test Eval",
            dataset_id="ds-1",
            agent_id="agent-1",
            agent_endpoint="http://test",
            status=EvaluationRunStatus.completed,
            test_cases=[]
        )
        mock_evaluator.get_evaluation_run = AsyncMock(return_value=mock_eval)
        
        with TestClient(app) as client:
            response = client.get("/api/evaluations/eval-123/results/non_existent")
            
            assert response.status_code == 404


# =============================================================================
# Functional Controller Tests - Cancel/Delete Evaluation
# =============================================================================

class TestCancelDeleteEvaluationFunctional:
    """Functional tests for cancel and delete evaluation endpoints."""
    
    def test_cancel_evaluation_success(self, app_with_mocks):
        """POST /api/evaluations/{id}/cancel should cancel running evaluation."""
        app, mock_db, mock_evaluator = app_with_mocks
        
        from src.api.models import EvaluationRun, EvaluationRunStatus
        cancelled_eval = EvaluationRun(
            id="eval-123",
            name="Test Eval",
            dataset_id="ds-1",
            agent_id="agent-1",
            agent_endpoint="http://test",
            status=EvaluationRunStatus.cancelled
        )
        mock_evaluator.cancel_evaluation_run = AsyncMock(return_value=cancelled_eval)
        
        with TestClient(app) as client:
            response = client.post("/api/evaluations/eval-123/cancel")
            
            assert response.status_code == 200
            assert response.json()["status"] == "cancelled"
    
    def test_cancel_evaluation_not_found(self, app_with_mocks):
        """POST /api/evaluations/{id}/cancel for non-existent should return 404."""
        app, mock_db, mock_evaluator = app_with_mocks
        # When evaluation not found, evaluator.cancel_evaluation_run returns None
        # but wrapped in try/except in controller - the exception path catches it
        mock_evaluator.cancel_evaluation_run = AsyncMock(return_value=None)
        
        with TestClient(app) as client:
            response = client.post("/api/evaluations/non_existent/cancel")
            
            # Controller should return 404 when cancel returns None
            assert response.status_code == 404
    
    def test_cancel_already_completed_evaluation(self, app_with_mocks):
        """POST /api/evaluations/{id}/cancel for completed should return 400."""
        app, mock_db, mock_evaluator = app_with_mocks
        mock_evaluator.cancel_evaluation_run = AsyncMock(
            side_effect=ValueError("Cannot cancel a completed evaluation")
        )
        
        with TestClient(app) as client:
            response = client.post("/api/evaluations/eval-123/cancel")
            
            assert response.status_code == 400
    
    def test_delete_evaluation_success(self, app_with_mocks):
        """DELETE /api/evaluations/{id} should delete evaluation."""
        app, mock_db, mock_evaluator = app_with_mocks
        mock_evaluator.delete_evaluation_run = AsyncMock(return_value=True)
        
        with TestClient(app) as client:
            response = client.delete("/api/evaluations/eval-123")
            
            assert response.status_code == 204
    
    def test_delete_evaluation_not_found(self, app_with_mocks):
        """DELETE /api/evaluations/{id} for non-existent should return 404."""
        app, mock_db, mock_evaluator = app_with_mocks
        mock_evaluator.delete_evaluation_run = AsyncMock(return_value=False)
        
        with TestClient(app) as client:
            response = client.delete("/api/evaluations/non_existent")
            
            assert response.status_code == 404
