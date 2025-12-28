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
        """Evaluating a test case with mock agent should produce tool calls."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        from src.api.models import TestCase, ToolExpectation, ArgumentAssertion, ResponseQualityAssertion
        
        # Create a test case that expects sendMail
        test_case = TestCase(
            dataset_id="ds_test",
            name="Email Test",
            description="Test that agent sends email",
            input="Send an email to the client",
            minimal_tool_set=["sendMail"],
            tool_expectations=[
                ToolExpectation(
                    name="sendMail",
                    arguments=[
                        ArgumentAssertion(
                            name="to",
                            assertion=["Should contain recipient email"]
                        )
                    ]
                )
            ],
            expected_response="Email sent successfully",
            response_quality_expectation=ResponseQualityAssertion(
                assertion="Agent should confirm email was sent"
            )
        )
        
        # Call mock agent
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/mock/invoke",
                json={"user_prompt": test_case.input}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify the agent called the expected tool
        tool_names = [tc["name"] for tc in data["tool_calls"]]
        assert "sendMail" in tool_names
        
        # Verify tool call has expected structure
        send_mail_call = next(tc for tc in data["tool_calls"] if tc["name"] == "sendMail")
        assert "to" in send_mail_call["arguments"]
        assert "subject" in send_mail_call["arguments"]
        assert "body" in send_mail_call["arguments"]
    
    @pytest.mark.asyncio
    async def test_evaluate_test_case_tool_mismatch(self):
        """Evaluating with wrong tool should be detectable."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        from src.api.models import TestCase, ToolExpectation
        
        # Create a test case that expects sendMail
        test_case = TestCase(
            dataset_id="ds_test",
            name="Email Test",
            description="Test that agent sends email",
            input="wrong_tool scenario",  # This triggers Teams instead of email
            minimal_tool_set=["sendMail"],
            tool_expectations=[
                ToolExpectation(name="sendMail", arguments=[])
            ],
            expected_response="Email sent"
        )
        
        # Call mock agent with wrong_tool prompt
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/mock/invoke",
                json={"user_prompt": test_case.input}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify the agent called the WRONG tool (Teams instead of email)
        tool_names = [tc["name"] for tc in data["tool_calls"]]
        assert "sendTeamsMessage" in tool_names
        assert "sendMail" not in tool_names
        
        # This would cause the test case to fail in the evaluator
        expected_tools = set(test_case.minimal_tool_set)
        actual_tools = set(tool_names)
        assert expected_tools != actual_tools  # Mismatch detected
    
    @pytest.mark.asyncio
    async def test_evaluate_meeting_workflow_complete(self):
        """Meeting agent should execute full workflow with all expected tools."""
        from tests.mocks.mock_agent_server import mock_agent_app
        from httpx import AsyncClient, ASGITransport
        from src.api.models import TestCase, ToolExpectation
        
        # Create a test case that expects the full meeting workflow
        test_case = TestCase(
            dataset_id="ds_test",
            name="Meeting Scheduler",
            description="Schedule a meeting with conflict checking",
            input="Schedule a meeting with John",
            minimal_tool_set=["searchMessages", "listEvents", "createEvent", "sendMail"],
            tool_expectations=[
                ToolExpectation(name="searchMessages", arguments=[]),
                ToolExpectation(name="listEvents", arguments=[]),
                ToolExpectation(name="createEvent", arguments=[]),
                ToolExpectation(name="sendMail", arguments=[]),
            ],
            expected_response="Meeting scheduled"
        )
        
        # Call mock meeting agent
        transport = ASGITransport(app=mock_agent_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agents/meeting/invoke",
                json={"user_prompt": test_case.input}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected tools were called
        actual_tools = {tc["name"] for tc in data["tool_calls"]}
        expected_tools = set(test_case.minimal_tool_set)
        
        assert expected_tools == actual_tools, f"Expected {expected_tools}, got {actual_tools}"
        
        # Verify tool call order makes sense (search before create)
        tool_order = [tc["name"] for tc in data["tool_calls"]]
        search_idx = tool_order.index("searchMessages")
        create_idx = tool_order.index("createEvent")
        assert search_idx < create_idx, "Should search before creating event"


class TestFullEvaluationPipeline:
    """End-to-end tests for the complete evaluation pipeline."""
    
    @pytest.mark.asyncio
    async def test_create_dataset_agent_and_evaluate(self, test_client, mock_cosmos_service):
        """Full flow: create dataset, agent, run evaluation, check results."""
        from src.api.models import Dataset, Metadata, SeedScenario, TestCase, Agent
        
        # 1. Create a dataset
        dataset = Dataset(
            metadata=Metadata(),
            seed=SeedScenario(
                name="Integration Test Dataset",
                goal="Test the full evaluation pipeline"
            )
        )
        await mock_cosmos_service.create_dataset(dataset)
        
        # 2. Create a test case for the dataset
        test_case = TestCase(
            dataset_id=dataset.id,
            name="Simple Email Test",
            description="Agent should send an email",
            input="Send an email to client@example.com",
            minimal_tool_set=["sendMail"],
            expected_response="Email sent"
        )
        await mock_cosmos_service.create_testcase(test_case)
        
        # 3. Create an agent
        agent = Agent(
            name="Mock Agent",
            agent_invocation_url="http://test/agents/mock/invoke",
            description="Mock agent for testing"
        )
        await mock_cosmos_service.create_agent(agent)
        
        # 4. Verify all entities were created
        retrieved_dataset = await mock_cosmos_service.get_dataset(dataset.id)
        assert retrieved_dataset is not None
        
        retrieved_agent = await mock_cosmos_service.get_agent(agent.id)
        assert retrieved_agent is not None
        
        test_cases = await mock_cosmos_service.list_testcases_by_dataset(dataset.id)
        assert len(test_cases) == 1
        assert test_cases[0].name == "Simple Email Test"
    
    @pytest.mark.asyncio
    async def test_evaluation_run_with_test_results(self, mock_cosmos_service):
        """Evaluation run should track test case results."""
        from src.api.models import (
            EvaluationRun, EvaluationRunStatus, TestCaseResult,
            ExpectedToolResult, ResponseQualityResult
        )
        
        # Create an evaluation run
        eval_run = EvaluationRun(
            name="Pipeline Test",
            dataset_id="ds_123",
            agent_id="agent_456",
            agent_endpoint="http://test/agents/mock/invoke",
            total_tests=2
        )
        await mock_cosmos_service.create_evaluation_run(eval_run)
        
        # Simulate test execution - first test passes
        test_result_1 = TestCaseResult(
            testcase_id="tc_001",
            passed=True,
            response_from_agent="Email sent to client@example.com",
            expected_tools=[
                ExpectedToolResult(name_of_tool="sendMail", was_called=True)
            ],
            tool_expectations=[],
            response_quality_assertion=ResponseQualityResult(
                passed=True,
                llm_judge_output="Agent correctly sent email"
            ),
            actual_tool_calls=[
                {"name": "sendMail", "arguments": {"to": ["client@example.com"]}}
            ]
        )
        
        # Simulate test execution - second test fails
        test_result_2 = TestCaseResult(
            testcase_id="tc_002",
            passed=False,
            response_from_agent="I sent a Teams message",
            expected_tools=[
                ExpectedToolResult(name_of_tool="sendMail", was_called=False)
            ],
            tool_expectations=[],
            response_quality_assertion=ResponseQualityResult(
                passed=False,
                llm_judge_output="Agent used wrong tool"
            ),
            actual_tool_calls=[
                {"name": "sendTeamsMessage", "arguments": {"channel": "general"}}
            ]
        )
        
        # Update evaluation run with results
        eval_run.test_cases = [test_result_1, test_result_2]
        eval_run.completed_tests = 2
        eval_run.passed_count = 1
        eval_run.failed_tests = 1
        eval_run.status = EvaluationRunStatus.completed
        eval_run.completed_at = datetime.now(timezone.utc)
        
        await mock_cosmos_service.update_evaluation_run(eval_run)
        
        # Retrieve and verify
        retrieved = await mock_cosmos_service.get_evaluation_run(eval_run.id)
        assert retrieved.status == EvaluationRunStatus.completed
        assert retrieved.total_tests == 2
        assert retrieved.passed_count == 1
        assert retrieved.failed_tests == 1
        assert len(retrieved.test_cases) == 2
        
        # Check individual results
        passed_test = next(tc for tc in retrieved.test_cases if tc.testcase_id == "tc_001")
        assert passed_test.passed is True
        
        failed_test = next(tc for tc in retrieved.test_cases if tc.testcase_id == "tc_002")
        assert failed_test.passed is False
    
    @pytest.mark.asyncio
    async def test_evaluation_tracks_tool_call_details(self, mock_cosmos_service):
        """Evaluation should preserve detailed tool call information."""
        from src.api.models import EvaluationRun, EvaluationRunStatus, TestCaseResult
        
        # Create evaluation with detailed tool call data
        tool_call_data = {
            "name": "sendMail",
            "arguments": {
                "to": ["client@example.com", "manager@example.com"],
                "cc": ["team@example.com"],
                "subject": "Project Update",
                "body": "Here is the status update..."
            },
            "response": {
                "success": True,
                "messageId": "msg_abc123"
            }
        }
        
        test_result = TestCaseResult(
            testcase_id="tc_detailed",
            passed=True,
            response_from_agent="Email sent with CC to team",
            expected_tools=[],
            tool_expectations=[],
            actual_tool_calls=[tool_call_data]
        )
        
        eval_run = EvaluationRun(
            name="Detail Test",
            dataset_id="ds_123",
            agent_id="agent_456",
            agent_endpoint="http://test/invoke",
            test_cases=[test_result],
            total_tests=1,
            completed_tests=1,
            passed_count=1,
            status=EvaluationRunStatus.completed
        )
        
        await mock_cosmos_service.create_evaluation_run(eval_run)
        
        # Retrieve and verify tool call details are preserved
        retrieved = await mock_cosmos_service.get_evaluation_run(eval_run.id)
        actual_calls = retrieved.test_cases[0].actual_tool_calls
        
        assert len(actual_calls) == 1
        assert actual_calls[0]["name"] == "sendMail"
        assert len(actual_calls[0]["arguments"]["to"]) == 2
        assert actual_calls[0]["arguments"]["cc"] == ["team@example.com"]
        assert actual_calls[0]["response"]["success"] is True


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
