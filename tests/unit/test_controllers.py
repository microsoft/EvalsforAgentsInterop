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
