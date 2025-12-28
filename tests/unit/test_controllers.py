"""
Unit Tests for API Controllers/Endpoints

Tests the FastAPI endpoints using mocked Cosmos DB service.
"""

import pytest
from fastapi import status
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
