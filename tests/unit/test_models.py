"""
Unit Tests for Pydantic Models

Tests the data validation, serialization, and default values for all API models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestMetadataModel:
    """Tests for the Metadata model."""
    
    def test_metadata_auto_generates_ids(self):
        """Metadata should auto-generate generator_id and suite_id."""
        from src.api.models import Metadata
        
        metadata = Metadata()
        
        assert metadata.generator_id.startswith("gen_")
        assert metadata.suite_id.startswith("suite_")
        assert metadata.version == "1.0"
        assert metadata.created_at is not None
    
    def test_metadata_with_custom_values(self):
        """Metadata should accept custom values."""
        from src.api.models import Metadata
        
        metadata = Metadata(
            generator_id="custom_gen",
            suite_id="custom_suite",
            version="2.0",
            schema_hash="hash123"
        )
        
        assert metadata.generator_id == "custom_gen"
        assert metadata.suite_id == "custom_suite"
        assert metadata.version == "2.0"
        assert metadata.schema_hash == "hash123"


class TestSeedScenarioModel:
    """Tests for the SeedScenario model."""
    
    def test_seed_scenario_requires_goal(self):
        """SeedScenario should require a goal field."""
        from src.api.models import SeedScenario
        
        with pytest.raises(ValidationError):
            SeedScenario()  # Missing required 'goal'
    
    def test_seed_scenario_with_goal(self):
        """SeedScenario should work with just a goal."""
        from src.api.models import SeedScenario
        
        scenario = SeedScenario(goal="Test goal")
        
        assert scenario.goal == "Test goal"
        assert scenario.name == ""
        assert scenario.input == {}


class TestRubricModel:
    """Tests for the Rubric model."""
    
    def test_rubric_requires_fields(self):
        """Rubric should require name, azure_foundry_id, and threshold."""
        from src.api.models import Rubric
        
        with pytest.raises(ValidationError):
            Rubric()
    
    def test_rubric_valid_creation(self):
        """Rubric should create with all required fields."""
        from src.api.models import Rubric
        
        rubric = Rubric(
            name="Test Rubric",
            azure_foundry_id="coherence",
            threshold=0.8
        )
        
        assert rubric.name == "Test Rubric"
        assert rubric.azure_foundry_id == "coherence"
        assert rubric.threshold == 0.8
        assert rubric.id.startswith("rubric_")


class TestArgumentAssertionModel:
    """Tests for the ArgumentAssertion model."""
    
    def test_argument_assertion_requires_name_and_assertion(self):
        """ArgumentAssertion should require name and assertion list."""
        from src.api.models import ArgumentAssertion
        
        with pytest.raises(ValidationError):
            ArgumentAssertion()
    
    def test_argument_assertion_valid_creation(self):
        """ArgumentAssertion should create with name and assertions."""
        from src.api.models import ArgumentAssertion
        
        arg = ArgumentAssertion(
            name="recipient",
            assertion=["Should be a valid email", "Should not be empty"]
        )
        
        assert arg.name == "recipient"
        assert len(arg.assertion) == 2
        assert arg.rubrics == []


class TestToolExpectationModel:
    """Tests for the ToolExpectation model."""
    
    def test_tool_expectation_requires_name(self):
        """ToolExpectation should require a name."""
        from src.api.models import ToolExpectation
        
        with pytest.raises(ValidationError):
            ToolExpectation()
    
    def test_tool_expectation_valid_creation(self):
        """ToolExpectation should create with name and optional arguments."""
        from src.api.models import ToolExpectation
        
        tool = ToolExpectation(name="sendMail")
        
        assert tool.name == "sendMail"
        assert tool.arguments == []


class TestDatasetModel:
    """Tests for the Dataset model."""
    
    def test_dataset_auto_generates_id(self):
        """Dataset should auto-generate an ID."""
        from src.api.models import Dataset, Metadata, SeedScenario
        
        dataset = Dataset(
            metadata=Metadata(),
            seed=SeedScenario(goal="Test goal")
        )
        
        assert dataset.id.startswith("dataset_")  # Actual prefix is 'dataset_'
        assert dataset.test_case_ids == []
    
    def test_dataset_serializes_datetime(self):
        """Dataset should serialize datetime to ISO format."""
        from src.api.models import Dataset, Metadata, SeedScenario
        
        dataset = Dataset(
            metadata=Metadata(),
            seed=SeedScenario(goal="Test goal")
        )
        
        data = dataset.model_dump()
        assert isinstance(data["created_at"], str)


class TestTestCaseModel:
    """Tests for the TestCase model."""
    
    def test_testcase_requires_dataset_id(self):
        """TestCase should require dataset_id."""
        from src.api.models import TestCase
        
        with pytest.raises(ValidationError):
            TestCase(
                description="Test description",
                input="Test input",
                expected_response="Expected response"
            )
    
    def test_testcase_valid_creation(self):
        """TestCase should create with required fields."""
        from src.api.models import TestCase
        
        tc = TestCase(
            dataset_id="ds_123",
            description="Test description",
            input="Test input",
            expected_response="Expected response"  # Required field
        )
        
        assert tc.dataset_id == "ds_123"
        assert tc.id.startswith("tc_")
        assert tc.minimal_tool_set == []


class TestAgentModel:
    """Tests for the Agent model."""
    
    def test_agent_auto_generates_id(self):
        """Agent should auto-generate an ID."""
        from src.api.models import Agent
        
        agent = Agent(
            name="Test Agent",
            description="A test agent",
            model="gpt-4o",
            agent_invocation_url="http://localhost:8001/invoke"
        )
        
        assert agent.id.startswith("agent_")
        assert agent.name == "Test Agent"
    
    def test_agent_serializes_datetime(self):
        """Agent should serialize createdAt to ISO format."""
        from src.api.models import Agent
        
        agent = Agent(
            name="Test Agent",
            description="A test agent",
            model="gpt-4o",
            agent_invocation_url="http://localhost:8001/invoke"
        )
        
        data = agent.model_dump()
        assert isinstance(data["createdAt"], str)


class TestEvaluationRunStatusEnum:
    """Tests for the EvaluationRunStatus enum."""
    
    def test_status_values_exist(self):
        """EvaluationRunStatus should have expected values."""
        from src.api.models import EvaluationRunStatus
        
        assert EvaluationRunStatus.pending == "pending"
        assert EvaluationRunStatus.running == "running"
        assert EvaluationRunStatus.completed == "completed"
        assert EvaluationRunStatus.failed == "failed"


class TestEvaluationRunModel:
    """Tests for the EvaluationRun model."""
    
    def test_evaluation_run_creation(self):
        """EvaluationRun should create with required fields."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        eval_run = EvaluationRun(
            name="Test Run",
            dataset_id="ds_123",
            agent_id="agent_123",
            agent_endpoint="http://localhost:8001/invoke"
        )
        
        assert eval_run.id.startswith("eval_")
        assert eval_run.status == EvaluationRunStatus.pending
        assert eval_run.total_tests == 0
        assert eval_run.test_cases == []
    
    def test_evaluation_run_default_values(self):
        """EvaluationRun should have sensible defaults."""
        from src.api.models import EvaluationRun
        
        eval_run = EvaluationRun(
            name="Test Run",
            dataset_id="ds_123",
            agent_id="agent_123",
            agent_endpoint="http://localhost:8001/invoke"
        )
        
        assert eval_run.agent_auth_required == True
        assert eval_run.timeout_seconds == 300
        assert eval_run.completed_tests == 0
        assert eval_run.failed_tests == 0
        assert eval_run.passed_count == 0


class TestTestCaseResultModel:
    """Tests for the TestCaseResult model."""
    
    def test_testcase_result_creation(self):
        """TestCaseResult should create with required fields."""
        from src.api.models import TestCaseResult
        
        result = TestCaseResult(
            testcase_id="tc_123",
            passed=True,
            response_from_agent="Success",
            expected_tools=[],
            tool_expectations=[]
        )
        
        assert result.testcase_id == "tc_123"
        assert result.passed == True
        assert result.actual_tool_calls == []
        assert result.execution_error is None


class TestAssertionResultModels:
    """Tests for assertion result models."""
    
    def test_assertion_result_creation(self):
        """AssertionResult should capture pass/fail with reasoning."""
        from src.api.models import AssertionResult
        
        result = AssertionResult(
            passed=True,
            llm_judge_output="The response includes 'Hello' - assertion passed"
        )
        
        assert result.passed == True
        assert "Hello" in result.llm_judge_output
    
    def test_expected_tool_result(self):
        """ExpectedToolResult should track if tool was called."""
        from src.api.models import ExpectedToolResult
        
        result = ExpectedToolResult(
            name_of_tool="sendMail",
            was_called=True
        )
        
        assert result.name_of_tool == "sendMail"
        assert result.was_called == True
