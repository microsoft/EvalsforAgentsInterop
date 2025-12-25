"""
Pytest Configuration and Fixtures

Provides shared fixtures for both unit and integration tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Configure event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# Mock Cosmos DB Service
# ==============================================================================

@pytest.fixture
def mock_cosmos_service():
    """Create a mock Cosmos DB service for testing without real database."""
    mock = AsyncMock()
    
    # In-memory storage for test data
    mock._datasets = {}
    mock._testcases = {}
    mock._agents = {}
    mock._evaluations = {}
    
    # Dataset operations
    async def create_dataset(dataset):
        mock._datasets[dataset.id] = dataset
        return dataset
    
    async def get_dataset(dataset_id):
        return mock._datasets.get(dataset_id)
    
    async def list_datasets(skip=0, limit=100):
        datasets = list(mock._datasets.values())
        return datasets[skip:skip+limit]
    
    async def delete_dataset(dataset_id):
        if dataset_id in mock._datasets:
            del mock._datasets[dataset_id]
            return True
        return False
    
    # Test case operations
    async def create_test_case(test_case):
        mock._testcases[test_case.id] = test_case
        return test_case
    
    async def get_test_case(test_case_id):
        return mock._testcases.get(test_case_id)
    
    async def get_test_cases_for_dataset(dataset_id):
        return [tc for tc in mock._testcases.values() if tc.dataset_id == dataset_id]
    
    async def delete_test_case(test_case_id):
        if test_case_id in mock._testcases:
            del mock._testcases[test_case_id]
            return True
        return False
    
    # Agent operations
    async def create_agent(agent):
        mock._agents[agent.id] = agent
        return agent
    
    async def get_agent(agent_id):
        return mock._agents.get(agent_id)
    
    async def list_agents(skip=0, limit=100):
        agents = list(mock._agents.values())
        return agents[skip:skip+limit]
    
    async def delete_agent(agent_id):
        if agent_id in mock._agents:
            del mock._agents[agent_id]
            return True
        return False
    
    # Evaluation operations
    async def create_evaluation_run(eval_run):
        mock._evaluations[eval_run.id] = eval_run
        return eval_run
    
    async def get_evaluation_run(eval_id):
        return mock._evaluations.get(eval_id)
    
    async def list_evaluation_runs(skip=0, limit=100):
        evals = list(mock._evaluations.values())
        return evals[skip:skip+limit]
    
    async def update_evaluation_run(eval_run):
        mock._evaluations[eval_run.id] = eval_run
        return eval_run
    
    async def delete_evaluation_run(eval_id):
        if eval_id in mock._evaluations:
            del mock._evaluations[eval_id]
            return True
        return False
    
    # Wire up the mock methods
    mock.create_dataset = create_dataset
    mock.get_dataset = get_dataset
    mock.list_datasets = list_datasets
    mock.delete_dataset = delete_dataset
    
    mock.create_test_case = create_test_case
    mock.get_test_case = get_test_case
    mock.get_test_cases_for_dataset = get_test_cases_for_dataset
    mock.delete_test_case = delete_test_case
    
    mock.create_agent = create_agent
    mock.get_agent = get_agent
    mock.list_agents = list_agents
    mock.delete_agent = delete_agent
    
    mock.create_evaluation_run = create_evaluation_run
    mock.get_evaluation_run = get_evaluation_run
    mock.list_evaluation_runs = list_evaluation_runs
    mock.update_evaluation_run = update_evaluation_run
    mock.delete_evaluation_run = delete_evaluation_run
    
    return mock


# ==============================================================================
# FastAPI Test Client Fixtures
# ==============================================================================

@pytest.fixture
def app_with_mocks(mock_cosmos_service):
    """Create a minimal FastAPI app with mocked dependencies for testing.
    
    Note: We create a simplified test app instead of importing the main app
    because the main app has MCP session manager that can't be reused across tests.
    """
    from fastapi import FastAPI
    from src.api.controllers import router
    
    # Patch the cosmos service and evaluator service
    with patch('src.api.controllers.db', mock_cosmos_service), \
         patch('src.api.controllers.evaluator') as mock_evaluator:
        
        # Create a simple test app without MCP
        test_app = FastAPI(title="Test API")
        test_app.include_router(router)
        
        @test_app.get("/")
        async def root():
            return {"message": "Evals for Agent Interop API", "docs": "/api/docs"}
        
        @test_app.get("/health")
        async def health():
            return {"status": "ok"}
        
        yield test_app, mock_cosmos_service, mock_evaluator


@pytest.fixture
def test_client(app_with_mocks):
    """Synchronous test client for simple endpoint tests."""
    app, _, _ = app_with_mocks
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app_with_mocks) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for async endpoint tests."""
    app, _, _ = app_with_mocks
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==============================================================================
# Sample Test Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_dataset_request():
    """Sample dataset creation request."""
    return {
        "name": "Test Dataset",
        "goal": "Test the email agent's ability to respond to client requests",
        "input": {"context": "test context"},
        "schema_hash": "abc123"
    }


@pytest.fixture
def sample_testcase_request():
    """Sample test case creation request."""
    return {
        "name": "Test Case 1",
        "description": "Test sending an email response",
        "input": "Please respond to the client about the project status",
        "minimal_tool_set": ["sendMail", "searchMessages"],
        "tool_expectations": [
            {
                "name": "sendMail",
                "arguments": [
                    {
                        "name": "to",
                        "assertion": ["The recipient should be the client email"],
                        "rubrics": []
                    }
                ]
            }
        ],
        "expected_response": "Email sent successfully"
    }


@pytest.fixture
def sample_agent_request():
    """Sample agent creation request."""
    return {
        "name": "Test Agent",
        "description": "A test agent for unit testing",
        "model": "gpt-4o",
        "agent_invocation_url": "http://localhost:8001/agents/calendar/invoke"
    }


@pytest.fixture
def sample_evaluation_request():
    """Sample evaluation run creation request."""
    return {
        "name": "Test Evaluation Run",
        "dataset_id": "test-dataset-id",
        "agent_id": "test-agent-id",
        "agent_endpoint": "http://localhost:8001/agents/calendar/invoke",
        "agent_auth_required": False,
        "timeout_seconds": 60
    }
