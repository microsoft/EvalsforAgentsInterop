"""
Integration Tests for Evaluation Pipeline

Tests the full evaluation flow from start to completion using mocked
agent and Cosmos DB services. These tests validate the end-to-end
behavior without requiring real Azure resources.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestEvaluationLifecycle:
    """Tests for the complete evaluation lifecycle."""
    
    @pytest.mark.asyncio
    async def test_evaluation_creation(self, async_client, sample_evaluation_request):
        """Creating an evaluation should initialize with pending status."""
        # This test validates the creation flow
        # In a real scenario, we'd create dataset and agent first
        pass  # Placeholder for full integration test
    
    @pytest.mark.asyncio
    async def test_evaluation_status_transitions(self):
        """Evaluation should transition: pending -> running -> completed."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        # Create an evaluation run
        eval_run = EvaluationRun(
            name="Test Run",
            dataset_id="ds_123",
            agent_id="agent_123",
            agent_endpoint="http://localhost:8002/agents/mock/invoke"
        )
        
        # Verify initial status
        assert eval_run.status == EvaluationRunStatus.pending
        
        # Simulate status transitions
        eval_run.status = EvaluationRunStatus.running
        eval_run.started_at = datetime.now(timezone.utc)
        assert eval_run.status == EvaluationRunStatus.running
        
        eval_run.status = EvaluationRunStatus.completed
        eval_run.completed_at = datetime.now(timezone.utc)
        assert eval_run.status == EvaluationRunStatus.completed


class TestMockAgentIntegration:
    """Tests using the mock agent server."""
    
    @pytest.mark.asyncio
    async def test_mock_agent_success_response(self):
        """Mock agent should return successful response."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/mock/invoke",
                json={"user_prompt": "Send an email to the client"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "tool_calls" in data
            assert len(data["tool_calls"]) > 0
            assert data["tool_calls"][0]["name"] == "sendMail"
    
    @pytest.mark.asyncio
    async def test_mock_agent_no_tools_scenario(self):
        """Mock agent should return no tools when prompted."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/mock/invoke",
                json={"user_prompt": "no_tools scenario"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["tool_calls"]) == 0
    
    @pytest.mark.asyncio
    async def test_mock_agent_rate_limit_simulation(self):
        """Mock agent should return 429 for rate limit test."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/mock/invoke",
                json={"user_prompt": "rate_limit test"}
            )
            
            assert response.status_code == 429
    
    @pytest.mark.asyncio
    async def test_mock_email_agent(self):
        """Email agent endpoint should return email-specific response."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/email/invoke",
                json={"user_prompt": "Reply to the client email"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tool_calls"][0]["name"] == "sendMail"
            assert "cc" in data["tool_calls"][0]["arguments"]
    
    @pytest.mark.asyncio
    async def test_mock_meeting_agent(self):
        """Meeting agent endpoint should return meeting workflow response."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/meeting/invoke",
                json={"user_prompt": "Schedule a meeting with the client"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify all 4 tools in the meeting workflow
            tool_names = [tc["name"] for tc in data["tool_calls"]]
            assert "searchMessages" in tool_names
            assert "listEvents" in tool_names
            assert "createEvent" in tool_names
            assert "sendMail" in tool_names


class TestEvaluationWithMockAgent:
    """Tests that combine the evaluation service with mock agent."""
    
    @pytest.mark.asyncio
    async def test_evaluate_test_case_success(self):
        """Evaluating a test case with mock agent should pass."""
        # This would be a more complete integration test
        # that wires up the evaluator service with mock agent
        pass  # Placeholder for future implementation
    
    @pytest.mark.asyncio
    async def test_evaluate_test_case_tool_mismatch(self):
        """Evaluating with wrong tool should fail assertions."""
        # Test that uses "wrong_tool" prompt to verify failure detection
        pass  # Placeholder for future implementation


class TestCosmosDBPersistence:
    """Tests for data persistence with mocked Cosmos DB."""
    
    @pytest.mark.asyncio
    async def test_dataset_crud_operations(self, mock_cosmos_service):
        """Dataset CRUD operations should work with mock service."""
        from src.api.models import Dataset, Metadata, SeedScenario
        
        # Create
        dataset = Dataset(
            metadata=Metadata(),
            seed=SeedScenario(goal="Test goal")
        )
        created = await mock_cosmos_service.create_dataset(dataset)
        assert created.id == dataset.id
        
        # Read
        retrieved = await mock_cosmos_service.get_dataset(dataset.id)
        assert retrieved is not None
        assert retrieved.id == dataset.id
        
        # List
        all_datasets = await mock_cosmos_service.list_datasets()
        assert len(all_datasets) == 1
        
        # Delete
        deleted = await mock_cosmos_service.delete_dataset(dataset.id)
        assert deleted == True
        
        # Verify deleted
        retrieved_after = await mock_cosmos_service.get_dataset(dataset.id)
        assert retrieved_after is None
    
    @pytest.mark.asyncio
    async def test_evaluation_run_persistence(self, mock_cosmos_service):
        """Evaluation runs should persist through mock service."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        # Create
        eval_run = EvaluationRun(
            name="Test Run",
            dataset_id="ds_123",
            agent_id="agent_123",
            agent_endpoint="http://localhost:8001/invoke"
        )
        created = await mock_cosmos_service.create_evaluation_run(eval_run)
        assert created.id == eval_run.id
        
        # Update
        eval_run.status = EvaluationRunStatus.running
        eval_run.completed_tests = 5
        updated = await mock_cosmos_service.update_evaluation_run(eval_run)
        assert updated.status == EvaluationRunStatus.running
        assert updated.completed_tests == 5
        
        # Retrieve and verify
        retrieved = await mock_cosmos_service.get_evaluation_run(eval_run.id)
        assert retrieved.status == EvaluationRunStatus.running
