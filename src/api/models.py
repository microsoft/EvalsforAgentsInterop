from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Annotated, Literal
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from enum import Enum

class Metadata(BaseModel):
    generator_id: str = Field(default_factory=lambda: f"gen_{uuid.uuid4().hex[:16]}", description="ID of the generator/pipeline")
    suite_id: str = Field(default_factory=lambda: f"suite_{uuid.uuid4().hex[:16]}", description="Logical ID for this suite/collection")
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Auto-generated timestamp")
    version: str = Field(default="1.0", description="Schema version")
    schema_hash: str = Field(default="", description="Canonical JSON hash of the payload")


class SeedScenario(BaseModel):
    name: str = Field(default="", description="Human-friendly name for the scenario")
    goal: str = Field(..., description="Goal outlined by the user")
    synthetic_domain: str = Field(default="", description="Synthetic domain or industry context for the scenario")
    input: Dict[str, Any] = Field(
        default_factory=dict
    )


class Rubric(BaseModel):
    """Configuration for an Azure Foundry evaluator call."""
    id: str = Field(default_factory=lambda: f"rubric_{uuid.uuid4().hex[:16]}", description="Local rubric id")
    name: str = Field(..., description="Human-friendly name")
    azure_foundry_id: str = Field(..., description="Evaluator identifier/class key in Azure Foundry")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Kwargs passed to the Azure evaluator (e.g., {'response': ..., 'ground_truth': ...})"
    )
    threshold: float = Field(..., description="Passing threshold for the evaluator's numeric score")


class ArgumentAssertion(BaseModel):
    """Natural-language assertion for an argument."""
    name: str = Field(..., description="Argument name")
    assertion: List[str] = Field(..., description="Natural language assertion for LLM-judge")
    rubrics: List[Rubric] = Field(
        default_factory=list,
        description="One or more Azure Foundry rubrics to evaluate this argument"
    )


class ToolExpectation(BaseModel):
    """Expected tool call and per-argument assertions."""
    name: str = Field(..., description="Tool name")
    arguments: List[ArgumentAssertion] = Field(default_factory=list, description="Per-argument checks")


class ResponseQualityAssertion(BaseModel):
    assertion: str = Field(..., description="Quality claim about the response to be LLM-judged")
    rubrics: List[Rubric] = Field(
        default_factory=list,
        description="One or more Azure Foundry rubrics to evaluate this argument"
    )


class MockStatus(str, Enum):
    ok = "ok"


class MockDocxResponse(BaseModel):
    """Response from the document mock."""
    title: str = Field(description="Document title", min_length=1, max_length=200)
    content_md: str = Field(description="Document content in Markdown format", min_length=10)
    status: MockStatus = Field(description="Status of mock")
    metadata: Dict[str, Any] | None = Field(default=None, description="Optional document metadata")
    sections: List[str] | None = Field(default=None, description="Optional list of section headings")


class MockEmailResponse(BaseModel):
    """Response from the email mock."""
    to: List[str] = Field(description="List of recipient email addresses", min_length=1)
    subject: str = Field(description="Email subject line", min_length=1, max_length=200)
    body_md: str = Field(description="Email body in Markdown format", min_length=10)
    status: MockStatus = Field(description="Status of mock")
    cc: List[str] | None = Field(default=None, description="Optional CC recipients")
    bcc: List[str] | None = Field(default=None, description="Optional BCC recipients")


class MockTeamsResponse(BaseModel):
    """Response from the Teams mock."""
    channel: str = Field(description="Teams channel name or identifier", min_length=1)
    message_md: str = Field(description="Message content in Markdown format", min_length=10)
    status: MockStatus = Field(description="Status of mock")
    mentions: List[str] | None = Field(default=None, description="Optional list of @mentions")
    attachments: List[str] | None = Field(default=None, description="Optional list of attachment names")


class DocxMock(MockDocxResponse):
    kind: Literal["docx"] = "docx"


class EmailMock(MockEmailResponse):
    kind: Literal["email"] = "email"


class TeamsMock(MockTeamsResponse):
    kind: Literal["teams"] = "teams"


ReferenceSeedItem = Annotated[
    Union[DocxMock, EmailMock, TeamsMock],
    Field(discriminator="kind")
]


class TestCase(BaseModel):
    id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:16]}", description="Id of the test case")
    dataset_id: str = Field(..., description="Id linking the test case to its parent dataset")
    name: Optional[str] = Field(default=None, description="Optional human-readable name for the test case")
    description: str
    input: str
    minimal_tool_set: List[str] = Field(default_factory=list)
    tool_expectations: List[ToolExpectation] = Field(default_factory=list)
    expected_response: str = Field(..., description="Expected response text for evaluation")
    response_quality_expectation: Optional[ResponseQualityAssertion] = None
    references_seed: Dict[str, Union[ReferenceSeedItem, List[ReferenceSeedItem]]] = Field(
        default_factory=dict,
        description="Inline mocks (docx/email/teams). Keys are logical names; values are mock(s) with 'kind' discriminator."
    )


# ========== Dataset Models ==========


class Dataset(BaseModel):
    """Internal model for storing datasets in Cosmos DB (without inline test_cases)"""
    id: str = Field(default_factory=lambda: f"dataset_{uuid.uuid4().hex[:16]}")
    metadata: Metadata
    seed: SeedScenario
    test_case_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvaluatorContract(BaseModel):
    """Complete evaluation dataset contract with inline test cases.
    Used for loading evaluation datasets from JSON files."""
    id: str
    metadata: Metadata
    seed: SeedScenario
    test_cases: List[TestCase]
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ========== API Response Models (Separated Storage) ==========

class DatasetResponse(BaseModel):
    """API response model for datasets (without inline test_cases)"""
    id: str
    metadata: Metadata
    seed: SeedScenario
    test_case_ids: List[str] = Field(default_factory=list)
    created_at: str


class TestCaseResponse(BaseModel):
    """API response model for test cases"""
    id: str
    dataset_id: str
    name: Optional[str] = None
    description: str
    input: str
    minimal_tool_set: List[str] = Field(default_factory=list)
    tool_expectations: List[ToolExpectation] = Field(default_factory=list)
    expected_response: str
    response_quality_expectation: Optional[ResponseQualityAssertion] = None
    references_seed: Dict[str, Any] = Field(default_factory=dict)


# ========== Request Models ==========

class CreateDatasetRequest(BaseModel):
    """Simplified request model for creating a new evaluation dataset"""
    name: str = Field(..., description="Human-friendly name for the dataset")
    goal: str = Field(..., description="Goal/description of what this dataset evaluates")
    input: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional input parameters")
    schema_hash: str = Field(default="", description="Optional schema hash")


class TestCaseCreate(BaseModel):
    """Request model for creating a test case (seed_id is taken from URL path)"""
    name: Optional[str] = None
    description: str
    input: str
    minimal_tool_set: List[str] = Field(default_factory=list)
    tool_expectations: List[ToolExpectation] = Field(default_factory=list)
    expected_response: str
    response_quality_expectation: Optional[ResponseQualityAssertion] = None
    references_seed: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Agent model for storing agent configurations"""

    id: str = Field(default_factory=lambda: f"agent_{datetime.now(timezone.utc).timestamp()}")
    name: str
    description: Optional[str] = ""
    model: Optional[str] = ""
    agent_invocation_url: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_serializer('createdAt')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class AgentCreate(BaseModel):
    """Request model for creating an agent"""
    name: str
    description: Optional[str] = ""
    model: Optional[str] = ""
    agent_invocation_url: str


# Evaluation Models
# New structured evaluation output models
class AssertionResult(BaseModel):
    """Result of evaluating a single assertion."""
    passed: bool
    llm_judge_output: str  # Combined feedback + reasoning


class ArgumentAssertionResult(BaseModel):
    """Results for assertions on a tool argument."""
    name_of_argument: str
    assertions: List[AssertionResult]


class ToolExpectationResult(BaseModel):
    """Results for tool expectations with argument assertions."""
    name_of_tool: str
    arguments: List[ArgumentAssertionResult]


class ExpectedToolResult(BaseModel):
    """Expected tool usage result."""
    name_of_tool: str
    was_called: bool


class ResponseQualityResult(BaseModel):
    """Result of response quality assertion."""
    passed: bool
    llm_judge_output: str


# ==============================================================================
# TEST CASE RESULT MODEL (Features: timing-metrics, rate-limit-retry)
# ==============================================================================
# This model captures the complete result of executing a single test case.
# It includes both the evaluation results AND operational metadata like:
# - Timing information for performance analysis
# - Retry counts for rate limit visibility
# - Actual tool calls for debugging agent behavior
# ==============================================================================
class TestCaseResult(BaseModel):
    """Structured result for a single test case.
    
    This model is persisted to Cosmos DB as part of the EvaluationRun document.
    It contains everything needed to understand what happened during the test.
    """
    testcase_id: str
    passed: bool  # Overall pass/fail based on all assertions and expected tools
    response_from_agent: str
    expected_tools: List[ExpectedToolResult]
    tool_expectations: List[ToolExpectationResult]
    response_quality_assertion: Optional[ResponseQualityResult] = None
    
    # Capture what the agent actually did for UI display
    # This includes the full tool call data with arguments and responses
    actual_tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    execution_error: Optional[str] = None  # Error message if execution failed
    
    # ==== RATE LIMIT TRACKING (Feature: rate-limit-retry) ====
    # This field tracks how many retries were needed due to Azure OpenAI rate limits.
    # A non-zero value here indicates the test encountered capacity issues.
    retry_count: int = Field(default=0, description="Number of retries due to rate limits")
    
    # ==== TIMING INFORMATION (Feature: timing-metrics) ====
    # These fields enable performance analysis of individual tests.
    # - agent_call_duration: Time spent calling the agent (including retries)
    # - judge_call_duration: Time spent on LLM judge calls (including retries)
    # - total_duration: End-to-end time including all phases
    completed_at: Optional[datetime] = Field(default=None, description="When this test case completed")
    agent_call_duration_seconds: Optional[float] = Field(default=None, description="Time taken for agent call including retries")
    judge_call_duration_seconds: Optional[float] = Field(default=None, description="Time taken for LLM judge calls including retries")
    total_duration_seconds: Optional[float] = Field(default=None, description="Total time for this test case")
    
    @field_serializer('completed_at')
    def serialize_completed_at(self, dt: Optional[datetime], _info) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat()


# ==============================================================================
# EVALUATION RUN STATUS ENUM (Feature: cancel-evaluation, orphan-cleanup)
# ==============================================================================
# Added 'cancelled' status to support manual cancellation and automatic
# cleanup of orphaned evaluations after server restarts.
# ==============================================================================
class EvaluationRunStatus(str, Enum):
    pending = "pending"      # Created but not yet started
    running = "running"      # Currently executing tests
    completed = "completed"  # All tests finished successfully
    failed = "failed"        # Evaluation failed with error
    cancelled = "cancelled"  # Manually cancelled OR orphaned after restart (Feature: cancel-evaluation)


# ==============================================================================
# STATUS HISTORY ENTRY (Features: status-updates, rate-limit-retry)
# ==============================================================================
# This model tracks the chronological history of status changes during
# evaluation execution. It enables:
# - Real-time progress visibility in the UI
# - Post-mortem analysis of what happened during an evaluation
# - Rate limit tracking with specific retry details
# ==============================================================================
class StatusHistoryEntry(BaseModel):
    """A timestamped status message for evaluation progress tracking.
    
    Each entry represents a notable event during evaluation execution.
    The UI uses this to show an activity log and highlight rate limit events.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
    
    # ==== RATE LIMIT DETAILS (Feature: rate-limit-retry) ====
    # These fields provide granular visibility into rate limit events.
    # When is_rate_limit=True, the other fields show retry details.
    is_rate_limit: bool = Field(default=False, description="Whether this entry is a rate limit event")
    retry_attempt: Optional[int] = Field(default=None, description="Which retry attempt (1-based)")
    max_attempts: Optional[int] = Field(default=None, description="Maximum retry attempts configured")
    wait_seconds: Optional[float] = Field(default=None, description="Seconds waiting before retry")
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()


# ==============================================================================
# EVALUATION RUN MODEL (Features: verbose-logging, status-updates, rate-limit-retry)
# ==============================================================================
# This is the main document stored in Cosmos DB for each evaluation.
# It contains:
# - Configuration (agent endpoint, timeout, verbose logging flag)
# - Progress tracking (completed/failed/passed counts)
# - Timestamps (created, started, completed)
# - Test case results (nested TestCaseResult objects)
# - Status history for real-time visibility (Feature: status-updates)
# - Rate limit statistics (Feature: rate-limit-retry)
# ==============================================================================
class EvaluationRun(BaseModel):
    """Evaluation run with structured test case results.
    
    This is the main evaluation document. It tracks the entire lifecycle
    of an evaluation from creation through completion.
    """
    
    id: str = Field(default_factory=lambda: f"eval_{datetime.now(timezone.utc).timestamp()}")
    name: str
    dataset_id: str
    agent_id: str
    status: EvaluationRunStatus = EvaluationRunStatus.pending
    
    # ==== CONFIGURATION ====
    agent_endpoint: str
    agent_auth_required: bool = True
    timeout_seconds: int = 300
    # Feature: verbose-logging - When True, logs each assertion being evaluated
    verbose_logging: bool = Field(default=False, description="Enable detailed assertion-level status updates")
    
    # ==== PROGRESS TRACKING ====
    total_tests: int = 0
    completed_tests: int = 0
    failed_tests: int = 0
    passed_count: int = 0
    
    # ==== TIMESTAMPS ====
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # ==== RESULTS ====
    test_cases: List[TestCaseResult] = []
    
    # ==== WARNINGS (Feature: rate-limit-retry) ====
    # Collects warning messages, primarily about rate limit retries.
    # These are displayed prominently in the UI.
    warnings: List[str] = Field(default_factory=list, description="Warnings encountered during evaluation")
    
    # ==== REAL-TIME STATUS (Feature: status-updates) ====
    # status_message: Current activity, polled by the UI for live updates
    # status_history: Complete chronological log for post-mortem analysis
    status_message: Optional[str] = Field(default=None, description="Current activity message for UI display")
    status_history: List[StatusHistoryEntry] = Field(default_factory=list, description="Chronological list of status messages")
    
    # Rate limit statistics
    total_rate_limit_hits: int = Field(default=0, description="Total number of rate limit errors encountered")
    total_retry_wait_seconds: float = Field(default=0.0, description="Total time spent waiting on retries")
    
    @field_serializer('created_at', 'started_at', 'completed_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        return dt.isoformat() if dt else None


class EvaluationRunCreate(BaseModel):
    name: str
    dataset_id: str
    agent_id: str
    agent_endpoint: str
    agent_auth_required: bool = True
    timeout_seconds: int = 300
    verbose_logging: bool = False


# ---------- MCP stuff ----------
class ToolCallResult(BaseModel):
    """Generic result model for tool calls"""
    success: bool = Field(..., description="Operation success status")
    tool_result_data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    

class McpToolLogEntry(BaseModel):
    """Log entry for MCP tool calls"""
    tool_name: str = Field(..., description="Name of the tool called")
    input_parameters: Dict[str, Any] = Field(..., description="Input parameters provided to the tool")
    result: ToolCallResult = Field(..., description="Result of the tool call")
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Auto-generated timestamp")


# ========== Exports ==========

__all__ = [
    'Dataset',
    'EvaluatorContract',
    'DatasetResponse',
    'TestCaseResponse',
    'CreateDatasetRequest',
    'TestCaseCreate',
    'Agent',
    'AgentCreate',
    'EvaluationRun',
    'EvaluationRunStatus',
    'EvaluationRunCreate',
    'TestCaseResult',
    'AssertionResult',
    'ArgumentAssertionResult',
    'ToolExpectationResult',
    'ExpectedToolResult',
    'ResponseQualityResult',
    'Metadata',
    'SeedScenario',
    'TestCase',
    'Rubric',
    'ToolExpectation',
    'ArgumentAssertion',
    'ResponseQualityAssertion',
    'ReferenceSeedItem',
    'MockStatus',
    'EmailMock',
    'TeamsMock',
    'DocxMock',
]
