"""
Evaluator Service for running async evaluations against agents.

==============================================================================
FEATURES IMPLEMENTED IN THIS MODULE:
==============================================================================

1. RATE LIMIT HANDLING WITH EXPONENTIAL BACKOFF (Feature: rate-limit-retry)
   - Automatic retry with exponential backoff when Azure OpenAI returns 429 errors
   - Configurable max attempts, base delay, and max delay via config.py
   - Jitter added to prevent thundering herd on retries
   - Status history tracks all rate limit events with timestamps
   - UI displays warnings and total retry wait time

2. VERBOSE LOGGING MODE (Feature: verbose-logging)
   - Optional per-evaluation flag to enable detailed assertion-level progress
   - When enabled, shows each tool and assertion being evaluated
   - Collapsed tool-level logging (Option D) to reduce noise
   - Pass/fail results displayed after each tool evaluation

3. REAL-TIME STATUS UPDATES (Feature: status-updates)
   - status_message field provides current activity for UI display
   - status_history maintains chronological log of all status changes
   - Test completion messages include percentage and failed items summary

4. ORPHAN EVALUATION CLEANUP (Feature: orphan-cleanup)
   - cleanup_orphaned_evaluations() cancels stuck evaluations on server restart
   - Adds status history entry explaining why evaluation was cancelled
   - Prevents accumulation of "running" evaluations that will never complete

5. EVALUATION CANCELLATION (Feature: cancel-evaluation)
   - cancel_evaluation_run() API endpoint to manually cancel evaluations
   - Properly marks evaluation as "cancelled" with completion timestamp
   - Cleans up associated locks to prevent resource leaks

6. TIMING TRACKING (Feature: timing-metrics)
   - Tracks agent_call_duration, judge_call_duration, total_duration per test
   - completed_at timestamp for each test case
   - Enables performance analysis and debugging slow tests

==============================================================================
"""

import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import httpx
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from .models import (
    EvaluationRun, EvaluationRunStatus, Agent, 
    ToolExpectation, TestCaseResult, ExpectedToolResult,
    ToolExpectationResult, ArgumentAssertionResult, AssertionResult,
    ResponseQualityResult
)
from .cosmos_service import CosmosDBService
from . import config

import logging
logger = logging.getLogger(__name__)

# Global OpenAI client instance (singleton pattern to reuse connection)
_openai_client = None


# ==============================================================================
# RETRY CONFIGURATION (Feature: rate-limit-retry)
# ==============================================================================
# These values can be overridden via environment variables in config.py:
# - RETRY_MAX_ATTEMPTS: Maximum number of retry attempts before giving up
# - RETRY_BASE_DELAY: Initial delay in seconds (doubles each attempt)
# - RETRY_MAX_DELAY: Maximum delay cap to prevent extremely long waits
# ==============================================================================
RETRY_MAX_ATTEMPTS = getattr(config, 'RETRY_MAX_ATTEMPTS', 5)
RETRY_BASE_DELAY = getattr(config, 'RETRY_BASE_DELAY', 2.0)
RETRY_MAX_DELAY = getattr(config, 'RETRY_MAX_DELAY', 60.0)


from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')


# ==============================================================================
# RETRY RESULT WRAPPER (Feature: rate-limit-retry)
# ==============================================================================
# This dataclass captures both the result of a retried operation AND metadata
# about how many retries occurred. This enables the UI to show users when
# their evaluations encountered rate limits and how long they had to wait.
# ==============================================================================
@dataclass
class RetryResult(Generic[T]):
    """Result from retry_with_backoff including retry statistics.
    
    Attributes:
        result: The actual return value from the wrapped function
        retry_count: Number of retries that occurred (0 = success on first try)
        had_rate_limit: True if any rate limit error was encountered
    """
    result: T
    retry_count: int
    had_rate_limit: bool


# ==============================================================================
# EXPONENTIAL BACKOFF RETRY WRAPPER (Feature: rate-limit-retry)
# ==============================================================================
# This is a reusable utility function that wraps any async function with
# automatic retry logic for rate limit errors. Key design decisions:
#
# 1. ONLY retries on rate limit errors (429, "too many requests", etc.)
#    - Other errors are raised immediately without retry
# 2. Uses exponential backoff: delay doubles each attempt (2s -> 4s -> 8s...)
# 3. Adds random jitter (0-10%) to prevent synchronized retries
# 4. Provides callback hook for status updates during retry waits
# 5. Returns metadata about retries for visibility in UI
# ==============================================================================
async def retry_with_backoff(func, *args, max_attempts=RETRY_MAX_ATTEMPTS, base_delay=RETRY_BASE_DELAY, on_retry=None, **kwargs) -> RetryResult:
    """
    Retry an async function with exponential backoff for rate limit errors.
    
    This function is designed to handle Azure OpenAI rate limits gracefully.
    It detects 429 errors (and similar rate limit messages) and automatically
    retries with increasing delays.
    
    Args:
        func: The async function to call
        max_attempts: Maximum number of retry attempts (default from config)
        base_delay: Base delay in seconds (will be doubled each retry)
        on_retry: Optional async callback(attempt, max_attempts, wait_time, error)
                  Called before each retry wait to allow status updates
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        RetryResult containing:
        - result: The function's return value
        - retry_count: How many retries occurred (0 = first attempt succeeded)
        - had_rate_limit: True if any rate limit was encountered
    
    Raises:
        The last exception if all retries fail or if a non-rate-limit error occurs
    
    Example:
        async def call_openai():
            return await client.chat.completions.create(...)
        
        result = await retry_with_backoff(call_openai, on_retry=update_status)
        if result.had_rate_limit:
            logger.warning(f"Completed with {result.retry_count} retries")
    """
    last_exception = None
    retry_count = 0
    
    for attempt in range(max_attempts):
        try:
            result = await func(*args, **kwargs)
            return RetryResult(result=result, retry_count=retry_count, had_rate_limit=retry_count > 0)
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if this is a rate limit error (429)
            # We check multiple patterns because different Azure services report this differently
            is_rate_limit = (
                '429' in error_str or 
                'rate' in error_str and 'limit' in error_str or
                'ratelimitreached' in error_str or
                'too many requests' in error_str
            )
            
            if not is_rate_limit:
                # Not a rate limit error, don't retry - raise immediately
                raise
            
            last_exception = e
            retry_count += 1
            
            if attempt < max_attempts - 1:
                # Calculate delay with exponential backoff + jitter
                delay = min(base_delay * (2 ** attempt), RETRY_MAX_DELAY)
                jitter = random.uniform(0, delay * 0.1)  # Add 0-10% jitter
                wait_time = delay + jitter
                
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{max_attempts}). "
                    f"Retrying in {wait_time:.1f}s... Error: {str(e)[:100]}"
                )
                
                # Call the optional retry callback before waiting
                if on_retry:
                    try:
                        await on_retry(attempt + 1, max_attempts, wait_time, str(e)[:100])
                    except Exception as cb_err:
                        logger.warning(f"on_retry callback failed: {cb_err}")
                
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Max retries ({max_attempts}) exceeded for rate limit error: {str(e)[:200]}")
    
    raise last_exception


# ==============================================================================
# INTERNAL TEST EXECUTION TRACKER (NOT PERSISTED)
# ==============================================================================
# This is a temporary in-memory object used during test execution to track:
# - Current status (pending/running/completed/failed)
# - Tool calls made by the agent
# - Agent's response text
# - Timing information for performance analysis (Feature: timing-metrics)
# - Retry counts for rate limit visibility (Feature: rate-limit-retry)
#
# IMPORTANT: This is NOT the same as TestCaseResult (which IS persisted).
# After a test completes, we build a TestCaseResult from this data.
# ==============================================================================
class _TestExecution:
    """Temporary tracking object for test execution state.
    
    This class holds ephemeral data during test execution. It is NOT persisted
    to the database. After the test completes, the data is used to construct
    a TestCaseResult which IS persisted.
    
    Attributes:
        test_case_id: ID of the test case being executed
        evaluation_run_id: ID of the parent evaluation run
        status: Current status (pending, running, completed, failed)
        agent_response: The text response from the agent
        tool_calls: Full tool call data from the agent (for UI display)
        actual_tools: List of tool names that were called
        error_message: Error details if execution failed
        test_case_result: Final result (built after execution completes)
        retry_count: Number of rate limit retries encountered
        had_rate_limit: Whether any rate limit was hit
        agent_call_start: Start time of agent HTTP call
        agent_call_duration: Time for agent HTTP call (including retries)
        judge_call_start: Start time of LLM judge phase
        judge_call_duration: Time for LLM judge calls (including retries)
        test_start: Start time of entire test
        total_duration: End-to-end time for this test
    """
    def __init__(self, test_case_id: str, evaluation_run_id: str):
        self.test_case_id = test_case_id
        self.evaluation_run_id = evaluation_run_id
        self.status = "pending"  # pending, running, completed, failed
        self.agent_response = ""
        self.tool_calls: List[Dict[str, Any]] = []
        self.actual_tools: List[str] = []
        self.error_message: Optional[str] = None
        # Result will be built here
        self.test_case_result: Optional[TestCaseResult] = None
        # Retry tracking (Feature: rate-limit-retry)
        self.retry_count: int = 0
        self.had_rate_limit: bool = False
        # Timing tracking
        self.agent_call_start: Optional[float] = None
        self.agent_call_duration: float = 0.0
        self.judge_call_start: Optional[float] = None
        self.judge_call_duration: float = 0.0
        self.test_start: Optional[float] = None
        self.total_duration: float = 0.0


class EvaluatorService:
    def __init__(self, cosmos_db: CosmosDBService, max_concurrent_tests: int = None):
        
        logger.info("Initializing EvaluatorService")
        logger.info(f"AZURE_OPENAI_ENDPOINT: {config.AZURE_OPENAI_ENDPOINT}")
        logger.info(f"AZURE_OPENAI_DEPLOYMENT: {config.AZURE_OPENAI_DEPLOYMENT}")

        self.db = cosmos_db
        self.openai_client = None
    
        # Use config default if not specified
        if max_concurrent_tests is None:
            max_concurrent_tests = config.MAX_CONCURRENT_TESTS
        self.max_concurrent_tests = max_concurrent_tests
        self._semaphore = asyncio.Semaphore(max_concurrent_tests)
        
        # Lock for protecting concurrent updates to evaluation runs
        self._eval_run_locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Lock to protect the locks dictionary

        logger.info("EvaluatorService initialized successfully")
    
    async def _update_status_message(
        self, 
        eval_run_id: str, 
        message: str,
        is_rate_limit: bool = False,
        retry_attempt: int = None,
        max_attempts: int = None,
        wait_seconds: float = None
    ):
        """Update the status message for real-time UI visibility and append to history.
        
        Args:
            eval_run_id: The evaluation run ID
            message: The status message
            is_rate_limit: Whether this is a rate limit event
            retry_attempt: Which retry attempt (1-based)
            max_attempts: Maximum retry attempts configured
            wait_seconds: Seconds waiting before retry
        """
        from .models import StatusHistoryEntry
        try:
            lock = await self._get_eval_run_lock(eval_run_id)
            async with lock:
                latest = await self.db.get_evaluation_run(eval_run_id)
                if latest and latest.status == EvaluationRunStatus.running:
                    latest.status_message = message
                    # Append to status history with rate limit details if applicable
                    latest.status_history.append(StatusHistoryEntry(
                        message=message,
                        is_rate_limit=is_rate_limit,
                        retry_attempt=retry_attempt,
                        max_attempts=max_attempts,
                        wait_seconds=wait_seconds
                    ))
                    
                    # Update aggregate rate limit stats
                    if is_rate_limit and wait_seconds:
                        latest.total_rate_limit_hits += 1
                        latest.total_retry_wait_seconds += wait_seconds
                    
                    await self.db.update_evaluation_run(latest)
                    logger.debug(f"Status message updated: {message}")
        except Exception as e:
            logger.warning(f"Failed to update status message: {e}")
    
    def OpenAIClientInitialization(self):
        """Initialize the OpenAI client globally if not already initialized."""
        global _openai_client
        
        if _openai_client is not None:
            self.openai_client = _openai_client
            return
        
        logger.info("Initializing OpenAI client")
        
        # Use API key if available, otherwise use DefaultAzureCredential
        if config.AZURE_OPENAI_API_KEY:
            logger.info("Using API key authentication")
            _openai_client = AzureOpenAI(
                api_version=config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
            )
        else:
            logger.info("Using DefaultAzureCredential authentication")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), 
                "https://cognitiveservices.azure.com/.default"
            )
            
            _openai_client = AzureOpenAI(
                api_version=config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
            )
        
        self.openai_client = _openai_client
        logger.info("OpenAI client initialized successfully")
        
    async def create_evaluation_run(self, run_request) -> EvaluationRun:
        """Create a new evaluation run and initialize test results."""
        
        # Get the dataset and its test cases
        dataset = await self.db.get_dataset(run_request.dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {run_request.dataset_id} not found")
            
        # Get test cases for this dataset
        test_cases = await self.db.list_testcases_by_dataset(run_request.dataset_id)
        
        agent = await self.db.get_agent(run_request.agent_id)
        if not agent:
            raise ValueError(f"Agent {run_request.agent_id} not found")
        
        # Create evaluation run
        eval_run = EvaluationRun(
            name=run_request.name,
            dataset_id=run_request.dataset_id,
            agent_id=run_request.agent_id,
            agent_endpoint=run_request.agent_endpoint,
            agent_auth_required=run_request.agent_auth_required,
            timeout_seconds=run_request.timeout_seconds,
            total_tests=len(test_cases),
            test_cases=[],  # Will be populated as tests complete
            verbose_logging=run_request.verbose_logging  # Pass through verbose logging flag
        )
        
        # Save to database
        saved_run = await self.db.create_evaluation_run(eval_run)
        return saved_run
    
    async def start_evaluation(self, evaluation_id: str):
        """Start the evaluation process asynchronously."""
        logger.info(f"Starting evaluation {evaluation_id}")
        
        eval_run = await self.db.get_evaluation_run(evaluation_id)
        if not eval_run:
            raise ValueError(f"Evaluation run {evaluation_id} not found")
        
        # Get test cases from dataset
        test_cases = await self.db.list_testcases_by_dataset(eval_run.dataset_id)
        if not test_cases:
            raise ValueError(f"No test cases found for dataset {eval_run.dataset_id}")
        
        # Update status to running
        eval_run.status = EvaluationRunStatus.running
        eval_run.started_at = datetime.now(timezone.utc)
        await self.db.update_evaluation_run(eval_run)
        
        try:
            # Create test execution trackers for each test case
            test_executions = [
                _TestExecution(test_case.id, eval_run.id)
                for test_case in test_cases
            ]
            
            # Process all test cases in parallel with controlled concurrency
            logger.info(f"Starting parallel execution of {len(test_executions)} test cases (max concurrent: {self.max_concurrent_tests})")
            
            # Create tasks for all test cases
            tasks = []
            for i, (test_exec, test_case) in enumerate(zip(test_executions, test_cases)):
                logger.info(f"Queuing test {i+1}/{len(test_executions)}: {test_case.id}")
                task = self._process_single_test_with_semaphore(eval_run, test_exec, test_case, i+1, len(test_executions))
                tasks.append(task)
            
            # Execute all tests in parallel with controlled concurrency
            logger.info(f"Waiting for all {len(tasks)} parallel tasks to complete...")
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"All parallel test execution completed.")
            
            # Fetch the latest evaluation run from DB to get all test results
            eval_run = await self.db.get_evaluation_run(eval_run.id)
            if not eval_run:
                raise ValueError(f"Evaluation run {eval_run.id} not found after test completion")
            
            # Calculate pass percentage
            pass_percentage = (eval_run.passed_count / eval_run.total_tests * 100) if eval_run.total_tests > 0 else 0
            
            logger.info(f"📊 Evaluation Results:")
            logger.info(f"   Total test cases: {eval_run.total_tests}")
            logger.info(f"   Passed: {eval_run.passed_count}")
            logger.info(f"   Failed: {eval_run.failed_tests}")
            logger.info(f"   Pass rate: {pass_percentage:.1f}%")
            
            # Calculate final results
            await self._finalize_evaluation(eval_run)
            
        except Exception as e:
            logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
            eval_run.status = EvaluationRunStatus.failed
            eval_run.completed_at = datetime.now(timezone.utc)
            await self.db.update_evaluation_run(eval_run)
            raise
    
    async def _process_single_test_with_semaphore(self, eval_run: EvaluationRun, test_exec: _TestExecution, test_case, test_num: int, total_tests: int):
        """Process a single test case with semaphore-controlled concurrency."""
        async with self._semaphore:
            await self._process_single_test(eval_run, test_exec, test_case, test_num, total_tests)
    
    async def _process_single_test(self, eval_run: EvaluationRun, test_exec: _TestExecution, test_case, test_num: int, total_tests: int):
        """Process a single test case (execute + judge) in parallel."""
        try:
            logger.info(f"Starting test {test_num}/{total_tests}: {test_case.id}")
            
            # Start timing the entire test
            test_exec.test_start = time.time()
            
            # Update status message for UI visibility
            await self._update_status_message(
                eval_run.id, 
                f"Running test {test_num}/{total_tests}: {test_case.name or test_case.id}"
            )
            
            # Update test execution status
            test_exec.status = "running"
            
            # Execute the test
            await self._execute_test(eval_run, test_exec, test_case)
            
            # Update status for judging phase with agent call timing
            await self._update_status_message(
                eval_run.id,
                f"Judging test {test_num}/{total_tests}: {test_case.name or test_case.id} (agent: {test_exec.agent_call_duration:.1f}s)"
            )
            
            # Run LLM judge and build result (only if execution was successful)
            if test_exec.status == "completed":
                await self._judge_and_build_result(eval_run, test_exec, test_case)
            else:
                # Execution failed - create a failed TestCaseResult
                logger.warning(f"Test {test_case.id} execution failed: {test_exec.error_message}")
                test_exec.total_duration = time.time() - test_exec.test_start if test_exec.test_start else 0
                test_exec.test_case_result = TestCaseResult(
                    testcase_id=test_case.id,
                    passed=False,
                    response_from_agent="",
                    expected_tools=[],
                    tool_expectations=[],
                    response_quality_assertion=None,
                    actual_tool_calls=test_exec.tool_calls,
                    execution_error=test_exec.error_message or "Execution failed",
                    retry_count=test_exec.retry_count,
                    completed_at=datetime.now(timezone.utc),
                    agent_call_duration_seconds=test_exec.agent_call_duration,
                    judge_call_duration_seconds=0.0,
                    total_duration_seconds=test_exec.total_duration
                )
            
            logger.info(f"Completed test {test_num}/{total_tests}: {test_case.id} - Status: {test_exec.status}, Passed: {test_exec.test_case_result.passed if test_exec.test_case_result else 'N/A'}")
            
            # Update status with completion, timing, and summary
            result_emoji = "✅" if test_exec.test_case_result and test_exec.test_case_result.passed else "❌"
            
            # Build summary with percentage and failed items
            summary = ""
            if test_exec.test_case_result:
                tc_result = test_exec.test_case_result
                
                # Track what passed and what failed
                passed_count = 0
                total_count = 0
                failed_items = []
                
                # Check tools called
                for tool in (tc_result.expected_tools or []):
                    total_count += 1
                    if tool.was_called:
                        passed_count += 1
                    else:
                        failed_items.append(f"{tool.name_of_tool} (not called)")
                
                # Check argument assertions
                for tool_exp in (tc_result.tool_expectations or []):
                    for arg in tool_exp.arguments:
                        total_count += 1
                        if all(a.passed for a in arg.assertions):
                            passed_count += 1
                        else:
                            failed_items.append(f"{tool_exp.name_of_tool}.{arg.name_of_argument}")
                
                # Check response quality
                if tc_result.response_quality_assertion:
                    total_count += 1
                    if tc_result.response_quality_assertion.passed:
                        passed_count += 1
                    else:
                        failed_items.append("Response Quality")
                
                # Calculate percentage
                pct = int((passed_count / total_count * 100)) if total_count > 0 else 0
                
                # Build summary string
                if failed_items:
                    # Limit to first 3 failed items to avoid very long messages
                    failed_str = ", ".join(failed_items[:3])
                    if len(failed_items) > 3:
                        failed_str += f" +{len(failed_items) - 3} more"
                    summary = f" | {pct}% | Failed: {failed_str}"
                else:
                    summary = f" | {pct}%"
            
            await self._update_status_message(
                eval_run.id,
                f"{result_emoji} Test {test_num}/{total_tests} done: {test_case.name or test_case.id} ({test_exec.agent_call_duration:.1f}s + {test_exec.judge_call_duration:.1f}s){summary}"
            )
            
            # Update Cosmos DB with this test result immediately
            if test_exec.test_case_result:
                await self._update_eval_run_with_test_result(eval_run, test_exec.test_case_result)
            
        except Exception as e:
            logger.error(f"Error processing test {test_case.id}: {str(e)}")
            test_exec.status = "failed"
            test_exec.error_message = f"Test processing failed: {str(e)}"
    
    async def _get_eval_run_lock(self, eval_run_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific evaluation run."""
        async with self._locks_lock:
            if eval_run_id not in self._eval_run_locks:
                self._eval_run_locks[eval_run_id] = asyncio.Lock()
            return self._eval_run_locks[eval_run_id]
    
    async def _update_eval_run_with_test_result(self, eval_run: EvaluationRun, test_result: TestCaseResult):
        """Update the evaluation run in Cosmos DB with a single test result.
        
        Uses a per-evaluation-run lock to prevent race conditions when multiple
        test threads try to update the same evaluation run simultaneously.
        """
        # Get the lock for this specific evaluation run
        lock = await self._get_eval_run_lock(eval_run.id)
        
        async with lock:
            try:
                # Fetch the latest eval run from DB
                latest_eval_run = await self.db.get_evaluation_run(eval_run.id)
                if not latest_eval_run:
                    logger.error(f"Could not find evaluation run {eval_run.id} to update")
                    return
                
                # Add the new test result
                latest_eval_run.test_cases.append(test_result)
                
                # Update counts
                latest_eval_run.completed_tests = len(latest_eval_run.test_cases)
                latest_eval_run.passed_count = sum(1 for tc in latest_eval_run.test_cases if tc.passed)
                latest_eval_run.failed_tests = latest_eval_run.completed_tests - latest_eval_run.passed_count
                
                # Add warning if rate limit retries occurred
                if test_result.retry_count > 0:
                    warning_msg = f"Test {test_result.testcase_id} required {test_result.retry_count} retry(ies) due to rate limits"
                    if warning_msg not in latest_eval_run.warnings:
                        latest_eval_run.warnings.append(warning_msg)
                        logger.info(f"Added rate limit warning for test {test_result.testcase_id}")
                
                # Save back to database
                await self.db.update_evaluation_run(latest_eval_run)
                
                logger.debug(f"Updated eval run {eval_run.id} with test result for {test_result.testcase_id} - Progress: {latest_eval_run.completed_tests}/{latest_eval_run.total_tests}")
                
            except Exception as e:
                logger.error(f"Error updating eval run with test result: {str(e)}")
    
    async def _execute_test(self, eval_run: EvaluationRun, test_exec: _TestExecution, test_case):
        """Execute a single test against the agent endpoint with retry logic for rate limits."""
        test_exec.agent_call_start = time.time()
        
        async def _make_agent_call():
            """Inner function to make the agent HTTP call (for retry wrapper)."""
            async with httpx.AsyncClient(timeout=eval_run.timeout_seconds) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-CorrelationId": eval_run.id,
                    "X-TestCaseId": test_case.id
                }
                
                # Prepare request payload
                payload = {
                    "dataset_id": eval_run.dataset_id,
                    "test_case_id": test_case.id,
                    "agent_id": eval_run.agent_id,
                    "evaluation_run_id": eval_run.id,
                    "input": test_case.input
                }
                
                # Call agent endpoint
                response = await client.post(
                    eval_run.agent_endpoint,
                    json=payload,
                    headers=headers
                )
                
                # Check for rate limit in response
                if response.status_code == 429:
                    raise Exception(f"HTTP 429: Rate limit reached - {response.text}")
                
                # Check for 500 errors that contain rate limit info
                if response.status_code == 500:
                    response_text = response.text
                    if '429' in response_text or 'RateLimitReached' in response_text:
                        raise Exception(f"HTTP 500 (rate limit): {response_text}")
                
                return response
        
        async def _on_agent_retry(attempt: int, max_attempts: int, wait_time: float, error: str):
            """Callback to log retry attempts to status history."""
            await self._update_status_message(
                eval_run.id,
                f"⚠️ Agent call rate limit (attempt {attempt}/{max_attempts}). Waiting {wait_time:.1f}s before retry...",
                is_rate_limit=True,
                retry_attempt=attempt,
                max_attempts=max_attempts,
                wait_seconds=wait_time
            )
        
        try:
            # Use retry wrapper for the agent call
            retry_result = await retry_with_backoff(_make_agent_call, on_retry=_on_agent_retry)
            response = retry_result.result
            
            # Track retries for visibility
            test_exec.retry_count += retry_result.retry_count
            if retry_result.had_rate_limit:
                test_exec.had_rate_limit = True
            
            if response.status_code == 200:
                result_data = response.json()
                test_exec.agent_response = result_data.get("response", "")
                
                # Extract tool calls
                tool_call_data = result_data.get("tool_calls", [])
                test_exec.tool_calls = tool_call_data
                test_exec.actual_tools = [
                    tool.get("name") if isinstance(tool, dict) else str(tool) 
                    for tool in tool_call_data
                ]
                
                test_exec.status = "completed"
                logger.info(f"Agent call successful for test {test_case.id}")
                
            else:
                test_exec.status = "failed"
                test_exec.error_message = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Agent call failed for test {test_case.id}: {test_exec.error_message}")
                
        except Exception as e:
            test_exec.status = "failed"
            test_exec.error_message = str(e)
            logger.error(f"Exception during test execution {test_case.id}: {str(e)}")
        finally:
            # Record agent call duration
            test_exec.agent_call_duration = time.time() - test_exec.agent_call_start
    
    async def _judge_and_build_result(self, eval_run: EvaluationRun, test_exec: _TestExecution, test_case):
        """Judge test execution and build TestCaseResult directly."""
        # Skip if execution failed
        if test_exec.status != "completed":
            logger.warning(f"Skipping judge for test {test_case.id} - execution status: {test_exec.status}")
            return
        
        # Start timing the judge phase
        test_exec.judge_call_start = time.time()
        
        # Initialize OpenAI client if needed
        self.OpenAIClientInitialization()
        
        try:
            # Get agent output as string
            response_from_agent = test_exec.agent_response
            
            # 1. Build expected_tools: check if each minimal_tool was called
            expected_tools = []
            for tool_name in test_case.minimal_tool_set:
                was_called = tool_name in test_exec.actual_tools
                expected_tools.append(ExpectedToolResult(
                    name_of_tool=tool_name,
                    was_called=was_called
                ))
            
            # 2. Build tool_expectations structure and evaluate assertions with LLM
            tool_expectations = []
            all_tool_assertions_passed = True
            
            # Pre-compute tool summary for verbose logging (Option D: collapse same-tool into one line)
            if eval_run.verbose_logging:
                from collections import defaultdict
                tool_summary = defaultdict(lambda: {'calls': 0, 'assertions': 0})
                for tool_exp in test_case.tool_expectations:
                    total_assertions = sum(len(arg.assertion) for arg in tool_exp.arguments)
                    tool_summary[tool_exp.name]['calls'] += 1
                    tool_summary[tool_exp.name]['assertions'] += total_assertions
                
                for tool_name, stats in tool_summary.items():
                    calls_text = f"{stats['calls']} call" + ("s" if stats['calls'] > 1 else "")
                    await self._update_status_message(
                        eval_run.id,
                        f"  📋 Evaluating {tool_name} ({calls_text}, {stats['assertions']} assertions)"
                    )
            
            for tool_idx, tool_exp in enumerate(test_case.tool_expectations):
                # Check if this tool was actually called
                tool_was_called = tool_exp.name in test_exec.actual_tools
                
                arg_results = []
                for arg_assertion in tool_exp.arguments:
                    assertions = []
                    for assertion_idx, assertion_text in enumerate(arg_assertion.assertion):
                        # Only evaluate assertion if the tool was called
                        # Otherwise, mark as failed with appropriate message
                        if not tool_was_called:
                            result = {
                                'passed': False,
                                'reasoning': f"Tool '{tool_exp.name}' was not called; cannot evaluate argument assertions."
                            }
                        else:
                            # Evaluate assertion with LLM
                            result = await self._evaluate_single_assertion(
                                eval_run=eval_run,
                                assertion_text=assertion_text,
                                tool_name=tool_exp.name,
                                argument_name=arg_assertion.name,
                                test_case=test_case,
                                test_exec=test_exec,
                                assertion_type="tool_argument"
                            )
                        
                        assertions.append(AssertionResult(
                            passed=result['passed'],
                            llm_judge_output=result['reasoning']
                        ))
                        
                        if not result['passed']:
                            all_tool_assertions_passed = False
                    
                    arg_results.append(ArgumentAssertionResult(
                        name_of_argument=arg_assertion.name,
                        assertions=assertions
                    ))
                
                tool_expectations.append(ToolExpectationResult(
                    name_of_tool=tool_exp.name,
                    arguments=arg_results
                ))
            
            # Log aggregated tool results in verbose mode
            if eval_run.verbose_logging and tool_expectations:
                for tool_result in tool_expectations:
                    # Count passed/failed arguments
                    passed_args = sum(1 for arg in tool_result.arguments 
                                     if all(a.passed for a in arg.assertions))
                    total_args = len(tool_result.arguments)
                    icon = "✓" if passed_args == total_args else "✗"
                    await self._update_status_message(
                        eval_run.id,
                        f"  {icon} {tool_result.name_of_tool}: {passed_args}/{total_args} arguments passed"
                    )
            
            # 3. Evaluate response quality assertion if present
            response_quality = None
            response_quality_passed = True
            
            if test_case.response_quality_expectation and hasattr(test_case.response_quality_expectation, 'assertion'):
                # Log response quality evaluation in verbose mode
                if eval_run.verbose_logging:
                    await self._update_status_message(
                        eval_run.id,
                        f"  📋 Evaluating response quality assertion"
                    )
                
                result = await self._evaluate_single_assertion(
                    eval_run=eval_run,
                    assertion_text=test_case.response_quality_expectation.assertion,
                    tool_name=None,
                    argument_name=None,
                    test_case=test_case,
                    test_exec=test_exec,
                    assertion_type="response_quality"
                )
                
                response_quality = ResponseQualityResult(
                    passed=result['passed'],
                    llm_judge_output=result['reasoning']
                )
                response_quality_passed = result['passed']
                
                # Log response quality result in verbose mode
                if eval_run.verbose_logging:
                    icon = "✓" if response_quality_passed else "✗"
                    await self._update_status_message(
                        eval_run.id,
                        f"  {icon} Response quality: {'passed' if response_quality_passed else 'failed'}"
                    )
            
            # 4. Calculate overall passed status
            all_tools_called = all(tool.was_called for tool in expected_tools)
            overall_passed = all_tools_called and all_tool_assertions_passed and response_quality_passed
            
            # Record judge call duration
            test_exec.judge_call_duration = time.time() - test_exec.judge_call_start if test_exec.judge_call_start else 0
            test_exec.total_duration = time.time() - test_exec.test_start if test_exec.test_start else 0
            
            # 5. Build final TestCaseResult
            test_exec.test_case_result = TestCaseResult(
                testcase_id=test_case.id,
                passed=overall_passed,
                response_from_agent=response_from_agent,
                expected_tools=expected_tools,
                tool_expectations=tool_expectations,
                response_quality_assertion=response_quality,
                actual_tool_calls=test_exec.tool_calls,  # Capture what agent actually did
                execution_error=None,  # No execution error if we got here
                retry_count=test_exec.retry_count,
                completed_at=datetime.now(timezone.utc),
                agent_call_duration_seconds=test_exec.agent_call_duration,
                judge_call_duration_seconds=test_exec.judge_call_duration,
                total_duration_seconds=test_exec.total_duration
            )
            
            logger.info(f"Test case {test_case.id} judged: passed={overall_passed} "
                       f"(tools: {all_tools_called}, assertions: {all_tool_assertions_passed}, quality: {response_quality_passed})")
            
        except Exception as e:
            logger.error(f"Error judging test {test_case.id}: {str(e)}")
            # Record timing even on failure
            test_exec.judge_call_duration = time.time() - test_exec.judge_call_start if test_exec.judge_call_start else 0
            test_exec.total_duration = time.time() - test_exec.test_start if test_exec.test_start else 0
            # Create a failed result
            test_exec.test_case_result = TestCaseResult(
                testcase_id=test_case.id,
                passed=False,
                response_from_agent=f"Judge error: {str(e)}",
                expected_tools=[],
                tool_expectations=[],
                response_quality_assertion=None,
                actual_tool_calls=test_exec.tool_calls,
                execution_error=f"Judge error: {str(e)}",
                retry_count=test_exec.retry_count,
                completed_at=datetime.now(timezone.utc),
                agent_call_duration_seconds=test_exec.agent_call_duration,
                judge_call_duration_seconds=test_exec.judge_call_duration,
                total_duration_seconds=test_exec.total_duration
            )
    
    async def _evaluate_single_assertion(self, eval_run: EvaluationRun, assertion_text, tool_name, argument_name, test_case, test_exec, assertion_type):
        """Evaluate a single assertion and return pass/fail result."""
        
        async def _on_judge_retry(attempt: int, max_attempts: int, wait_time: float, error: str):
            """Callback to log LLM judge retry attempts to status history."""
            await self._update_status_message(
                eval_run.id,
                f"⚠️ LLM judge rate limit (attempt {attempt}/{max_attempts}). Waiting {wait_time:.1f}s...",
                is_rate_limit=True,
                retry_attempt=attempt,
                max_attempts=max_attempts,
                wait_seconds=wait_time
            )
        
        if assertion_type == "tool_argument":
            context_prompt = f"""
**Tool:** {tool_name}
**Argument:** {argument_name}
**Assertion:** {assertion_text}

**Agent's Tool Calls:** {json.dumps(test_exec.tool_calls, indent=2)}
**Actual Tools Used:** {', '.join(test_exec.actual_tools)}

Evaluate if the agent's tool usage satisfies this specific assertion.
"""
        else:  # response_quality
            context_prompt = f"""
**Response Quality Assertion:** {assertion_text}

**Agent Output:** {test_exec.agent_response if test_exec.agent_response else "No output"}
**Expected Response:** {test_case.expected_response}

Evaluate if the agent's response satisfies this quality assertion.
"""
        
        judge_prompt = f"""
You are evaluating a specific assertion about an AI agent's performance.

**Test Context:**
- Input: {test_case.input}
- Description: {test_case.description}

{context_prompt}

**Task:** Determine if this assertion is satisfied (True/False).

Respond in JSON format with a single human-readable sentence explanation:
{{
    "passed": true,
    "reasoning": "One sentence explaining why this assertion passed or failed."
}}
"""
        
        async def _call_llm_judge():
            """Inner function to call the LLM judge (for retry wrapper)."""
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                response_format={"type": "json_object"}  # Force JSON mode
            )
            return response
        
        try:
            messages = [
                {"role": "system", "content": "You are a precise evaluator. Assess each assertion objectively and return ONLY valid JSON with no additional text. Keep reasoning to ONE sentence only. Return only True if the assertion is clearly satisfied."},
                {"role": "user", "content": judge_prompt}
            ]
            
            # Use retry wrapper for the LLM call with status updates
            retry_result = await retry_with_backoff(_call_llm_judge, on_retry=_on_judge_retry)
            response = retry_result.result
            
            # Track retries for visibility
            test_exec.retry_count += retry_result.retry_count
            if retry_result.had_rate_limit:
                test_exec.had_rate_limit = True
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"LLM response for assertion: {content[:200]}...")
            
            # Try to parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse LLM response as JSON: {content[:500]}")
                logger.error(f"JSON decode error: {str(je)}")
                # Return a failed result with the raw content as reasoning
                return {
                    "passed": False,
                    "reasoning": f"LLM returned invalid JSON. Raw response: {content[:200]}"
                }
            
            return {
                "passed": bool(result.get("passed", False)),
                "reasoning": result.get("reasoning", "No reasoning provided")
            }
            
        except Exception as e:
            logger.error(f"Error evaluating assertion '{assertion_text}': {str(e)}", exc_info=True)
            return {
                "passed": False,
                "reasoning": f"Evaluation failed: {str(e)}"
            }
    
    async def _finalize_evaluation(self, eval_run: EvaluationRun):
        """Calculate final results and update evaluation status."""
        
        # Update final status
        eval_run.status = EvaluationRunStatus.completed
        eval_run.completed_at = datetime.now(timezone.utc)
        
        await self.db.update_evaluation_run(eval_run)
        
        pass_percentage = (eval_run.passed_count / eval_run.total_tests * 100) if eval_run.total_tests > 0 else 0
        logger.info(f"Evaluation {eval_run.id} completed: {eval_run.passed_count}/{eval_run.total_tests} passed ({pass_percentage:.1f}%)")
        
        # Clean up the lock for this evaluation run
        async with self._locks_lock:
            self._eval_run_locks.pop(eval_run.id, None)
    
    async def cancel_evaluation_run(self, evaluation_id: str) -> Optional[EvaluationRun]:
        """Cancel a running or stuck evaluation.
        
        Marks the evaluation as cancelled and sets completion time.
        This is useful for cleaning up orphaned evaluations after restarts.
        
        Args:
            evaluation_id: The ID of the evaluation to cancel
            
        Returns:
            The updated EvaluationRun, or None if not found
            
        Raises:
            ValueError: If the evaluation is already completed
        """
        eval_run = await self.db.get_evaluation_run(evaluation_id)
        if not eval_run:
            return None
        
        # Check if already in a terminal state
        if eval_run.status in [EvaluationRunStatus.completed, EvaluationRunStatus.failed]:
            raise ValueError(f"Cannot cancel evaluation in '{eval_run.status}' state")
        
        # Mark as cancelled
        eval_run.status = EvaluationRunStatus.cancelled
        eval_run.completed_at = datetime.now(timezone.utc)
        
        await self.db.update_evaluation_run(eval_run)
        
        logger.info(f"Evaluation {evaluation_id} cancelled. Progress: {eval_run.completed_tests}/{eval_run.total_tests}")
        
        # Clean up any locks for this evaluation
        async with self._locks_lock:
            self._eval_run_locks.pop(evaluation_id, None)
        
        return eval_run
    
    async def cleanup_orphaned_evaluations(self):
        """Mark any 'running' or 'pending' evaluations as cancelled.
        
        This should be called at startup to clean up evaluations that were
        interrupted by a server restart.
        """
        from .models import StatusHistoryEntry
        try:
            # Get all evaluations
            all_evals = await self.db.list_evaluation_runs(limit=1000)
            
            orphaned_count = 0
            for eval_run in all_evals:
                if eval_run.status in [EvaluationRunStatus.running, EvaluationRunStatus.pending]:
                    eval_run.status = EvaluationRunStatus.cancelled
                    eval_run.completed_at = datetime.now(timezone.utc)
                    # Add status history entry explaining the cancellation
                    eval_run.status_history.append(StatusHistoryEntry(
                        message="⚠️ Cancelled: Server restarted while evaluation was running"
                    ))
                    await self.db.update_evaluation_run(eval_run)
                    orphaned_count += 1
                    print(f"[STARTUP] Marked orphaned evaluation {eval_run.id} ({eval_run.name}) as cancelled", flush=True)
            
            if orphaned_count > 0:
                print(f"[STARTUP] Cleaned up {orphaned_count} orphaned evaluation(s)", flush=True)
            else:
                print("[STARTUP] No orphaned evaluations found", flush=True)
                
        except Exception as e:
            print(f"[STARTUP ERROR] Orphaned evaluation cleanup failed: {str(e)}", flush=True)
    
    async def get_evaluation_run(self, evaluation_id: str) -> Optional[EvaluationRun]:
        return await self.db.get_evaluation_run(evaluation_id)
    
    async def list_evaluation_runs(self, skip: int = 0, limit: int = 100, agent_id: Optional[str] = None) -> List[EvaluationRun]:
        return await self.db.list_evaluation_runs(skip=skip, limit=limit, agent_id=agent_id)
    
    async def delete_evaluation_run(self, evaluation_id: str) -> bool:
        return await self.db.delete_evaluation_run(evaluation_id)


# Service instance
_evaluator_service: Optional[EvaluatorService] = None


def get_evaluator_service(cosmos_db: CosmosDBService, max_concurrent_tests: int = None) -> EvaluatorService:
    """Get or create the evaluator service instance."""
    global _evaluator_service
    if _evaluator_service is None:
        _evaluator_service = EvaluatorService(cosmos_db, max_concurrent_tests)
    return _evaluator_service