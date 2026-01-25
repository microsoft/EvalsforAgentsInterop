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
        
        assert EvaluationRunStatus.pending.value == "pending"
        assert EvaluationRunStatus.running.value == "running"
        assert EvaluationRunStatus.completed.value == "completed"
        assert EvaluationRunStatus.failed.value == "failed"
    
    def test_status_cancelled(self):
        """Should have cancelled status (new feature)."""
        from src.api.models import EvaluationRunStatus
        
        assert EvaluationRunStatus.cancelled.value == "cancelled"
    
    def test_all_expected_statuses_exist(self):
        """All expected status values should be defined."""
        from src.api.models import EvaluationRunStatus
        
        expected = ["pending", "running", "completed", "failed", "cancelled"]
        actual = [s.value for s in EvaluationRunStatus]
        
        for status in expected:
            assert status in actual, f"Missing status: {status}"


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


# =============================================================================
# Tests for API Evaluation Improvements
# =============================================================================
# These tests validate the enhanced features:
# - StatusHistoryEntry for rate-limit tracking
# - EvaluationRun timing, status history, and progress fields
# - EvaluationRunStatus.cancelled enum value
# - Configuration settings for retry and rate limiting
# =============================================================================


class TestStatusHistoryEntry:
    """Tests for the StatusHistoryEntry model used for rate-limit tracking."""
    
    def test_status_history_entry_creation(self):
        """StatusHistoryEntry should capture rate limit events."""
        from src.api.models import StatusHistoryEntry
        
        entry = StatusHistoryEntry(
            message="Rate limit hit, waiting 30 seconds"
        )
        
        assert entry.message == "Rate limit hit, waiting 30 seconds"
        assert entry.timestamp is not None
    
    def test_status_history_entry_auto_timestamp(self):
        """StatusHistoryEntry should auto-generate timestamp."""
        from src.api.models import StatusHistoryEntry
        
        before = datetime.now(timezone.utc)
        entry = StatusHistoryEntry(message="Test message")
        after = datetime.now(timezone.utc)
        
        assert before <= entry.timestamp <= after
    
    def test_status_history_entry_with_rate_limit_info(self):
        """StatusHistoryEntry should support rate limit tracking fields."""
        from src.api.models import StatusHistoryEntry
        
        entry = StatusHistoryEntry(
            message="Rate limit hit",
            is_rate_limit=True,
            retry_attempt=2,
            max_attempts=5,
            wait_seconds=30.0
        )
        
        assert entry.is_rate_limit is True
        assert entry.retry_attempt == 2
        assert entry.max_attempts == 5
        assert entry.wait_seconds == 30.0
    
    def test_status_history_entry_default_values(self):
        """StatusHistoryEntry should have sensible defaults."""
        from src.api.models import StatusHistoryEntry
        
        entry = StatusHistoryEntry(message="Test")
        
        assert entry.is_rate_limit is False
        assert entry.retry_attempt is None
        assert entry.max_attempts is None
        assert entry.wait_seconds is None


class TestEvaluationRunEnhancements:
    """Tests for enhanced EvaluationRun model fields."""
    
    def test_evaluation_run_has_status_history(self):
        """EvaluationRun should have status_history field."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.pending
        )
        
        assert hasattr(run, "status_history")
        assert run.status_history == []
    
    def test_evaluation_run_with_status_history(self):
        """EvaluationRun should store status history entries."""
        from src.api.models import EvaluationRun, EvaluationRunStatus, StatusHistoryEntry
        
        history = [
            StatusHistoryEntry(message="Evaluation started"),
            StatusHistoryEntry(message="Rate limit hit, retrying", is_rate_limit=True),
        ]
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.running,
            status_history=history
        )
        
        assert len(run.status_history) == 2
        assert run.status_history[1].is_rate_limit is True
    
    def test_evaluation_run_has_timing_fields(self):
        """EvaluationRun should have timing metric fields."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.completed
        )
        
        assert hasattr(run, "started_at")
        assert hasattr(run, "completed_at")
        assert hasattr(run, "created_at")
    
    def test_evaluation_run_has_rate_limit_tracking(self):
        """EvaluationRun should have rate limit tracking fields."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.running,
            total_rate_limit_hits=3,
            total_retry_wait_seconds=45.5
        )
        
        assert run.total_rate_limit_hits == 3
        assert run.total_retry_wait_seconds == 45.5
    
    def test_evaluation_run_has_verbose_logging(self):
        """EvaluationRun should support verbose logging flag."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.pending,
            verbose_logging=True
        )
        
        assert run.verbose_logging is True
    
    def test_evaluation_run_cancelled_status(self):
        """EvaluationRun should support cancelled status."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.cancelled
        )
        
        assert run.status == EvaluationRunStatus.cancelled
    
    def test_evaluation_run_progress_tracking(self):
        """EvaluationRun should track test progress."""
        from src.api.models import EvaluationRun, EvaluationRunStatus
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.running,
            total_tests=10,
            completed_tests=5,
            passed_count=4,
            failed_tests=1
        )
        
        assert run.total_tests == 10
        assert run.completed_tests == 5
        assert run.passed_count == 4
        assert run.failed_tests == 1


class TestCancelledEvaluationFlow:
    """Tests for evaluation cancellation scenarios."""
    
    def test_evaluation_can_transition_to_cancelled(self):
        """Evaluation should be able to transition to cancelled status."""
        from src.api.models import EvaluationRun, EvaluationRunStatus, StatusHistoryEntry
        
        run = EvaluationRun(
            id="eval_123",
            name="Test Run",
            dataset_id="ds_456",
            agent_id="agent_789",
            agent_endpoint="http://localhost:8001",
            status=EvaluationRunStatus.running,
            status_history=[
                StatusHistoryEntry(message="Started"),
            ]
        )
        
        # Simulate cancellation
        run.status = EvaluationRunStatus.cancelled
        run.status_history.append(
            StatusHistoryEntry(message="Cancelled by user")
        )
        
        assert run.status == EvaluationRunStatus.cancelled
        assert len(run.status_history) == 2
        assert run.status_history[-1].message == "Cancelled by user"


class TestConfigurationSettings:
    """Tests for configuration settings related to evaluation improvements."""
    
    def test_config_has_retry_max_attempts(self):
        """Config should have RETRY_MAX_ATTEMPTS setting."""
        from src.api import config
        
        assert hasattr(config, "RETRY_MAX_ATTEMPTS")
        assert isinstance(config.RETRY_MAX_ATTEMPTS, int)
        assert config.RETRY_MAX_ATTEMPTS > 0
    
    def test_config_has_retry_base_delay(self):
        """Config should have RETRY_BASE_DELAY setting."""
        from src.api import config
        
        assert hasattr(config, "RETRY_BASE_DELAY")
        assert config.RETRY_BASE_DELAY > 0
    
    def test_config_has_retry_max_delay(self):
        """Config should have RETRY_MAX_DELAY setting."""
        from src.api import config
        
        assert hasattr(config, "RETRY_MAX_DELAY")
        assert config.RETRY_MAX_DELAY >= config.RETRY_BASE_DELAY
    
    def test_config_has_evaluation_timeout(self):
        """Config should have EVALUATION_TIMEOUT_SECONDS setting."""
        from src.api import config
        
        assert hasattr(config, "EVALUATION_TIMEOUT_SECONDS")
        assert isinstance(config.EVALUATION_TIMEOUT_SECONDS, int)


class TestEvaluationRunCreateEnhancements:
    """Tests for EvaluationRunCreate request model enhancements."""
    
    def test_evaluation_run_create_basic(self):
        """EvaluationRunCreate should accept required fields."""
        from src.api.models import EvaluationRunCreate
        
        request = EvaluationRunCreate(
            name="Test Evaluation",
            dataset_id="ds_123",
            agent_id="agent_456",
            agent_endpoint="http://localhost:8001"
        )
        
        assert request.name == "Test Evaluation"
        assert request.dataset_id == "ds_123"
        assert request.agent_id == "agent_456"
        assert request.agent_endpoint == "http://localhost:8001"
    
    def test_evaluation_run_create_with_verbose(self):
        """EvaluationRunCreate should support verbose_logging option."""
        from src.api.models import EvaluationRunCreate
        
        request = EvaluationRunCreate(
            name="Test Evaluation",
            dataset_id="ds_123",
            agent_id="agent_456",
            agent_endpoint="http://localhost:8001",
            verbose_logging=True
        )
        
        assert request.verbose_logging is True
    
    def test_evaluation_run_create_requires_name(self):
        """EvaluationRunCreate should require name field."""
        from src.api.models import EvaluationRunCreate
        
        with pytest.raises(ValidationError):
            EvaluationRunCreate(
                dataset_id="ds_123",
                agent_id="agent_456",
                agent_endpoint="http://localhost:8001"
            )
    
    def test_evaluation_run_create_requires_endpoint(self):
        """EvaluationRunCreate should require agent_endpoint field."""
        from src.api.models import EvaluationRunCreate
        
        with pytest.raises(ValidationError):
            EvaluationRunCreate(
                name="Test",
                dataset_id="ds_123",
                agent_id="agent_456"
            )
