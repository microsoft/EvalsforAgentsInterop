"""
Evaluator Service for running async evaluations against agents.
"""

import asyncio
import json
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

# Global OpenAI client instance
_openai_client = None


# Internal tracking class for test execution (not persisted)
class _TestExecution:
    """Temporary tracking object for test execution state."""
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
            test_cases=[]  # Will be populated as tests complete
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
            
            # Update test execution status
            test_exec.status = "running"
            
            # Execute the test
            await self._execute_test(eval_run, test_exec, test_case)
            
            # Run LLM judge and build result (only if execution was successful)
            if test_exec.status == "completed":
                await self._judge_and_build_result(test_exec, test_case)
            else:
                # Execution failed - create a failed TestCaseResult
                logger.warning(f"Test {test_case.id} execution failed: {test_exec.error_message}")
                test_exec.test_case_result = TestCaseResult(
                    testcase_id=test_case.id,
                    passed=False,
                    response_from_agent="",
                    expected_tools=[],
                    tool_expectations=[],
                    response_quality_assertion=None,
                    actual_tool_calls=test_exec.tool_calls,
                    execution_error=test_exec.error_message or "Execution failed"
                )
            
            logger.info(f"Completed test {test_num}/{total_tests}: {test_case.id} - Status: {test_exec.status}, Passed: {test_exec.test_case_result.passed if test_exec.test_case_result else 'N/A'}")
            
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
                
                # Save back to database
                await self.db.update_evaluation_run(latest_eval_run)
                
                logger.debug(f"Updated eval run {eval_run.id} with test result for {test_result.testcase_id} - Progress: {latest_eval_run.completed_tests}/{latest_eval_run.total_tests}")
                
            except Exception as e:
                logger.error(f"Error updating eval run with test result: {str(e)}")
    
    async def _execute_test(self, eval_run: EvaluationRun, test_exec: _TestExecution, test_case):
        """Execute a single test against the agent endpoint."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=eval_run.timeout_seconds) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-CorrelationId": eval_run.id,
                    "X-TestCaseId": test_case.id
                }
                
                '''
                # Add authentication if required
                if eval_run.agent_auth_required:
                    # Use Azure AD token
                    credential = DefaultAzureCredential()
                    token_provider = get_bearer_token_provider(
                        credential, 
                        "https://cognitiveservices.azure.com/.default"
                    )
                    token = token_provider()
                    headers["Authorization"] = f"Bearer {token}"
                '''
                
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
    
    async def _judge_and_build_result(self, test_exec: _TestExecution, test_case):
        """Judge test execution and build TestCaseResult directly."""
        # Skip if execution failed
        if test_exec.status != "completed":
            logger.warning(f"Skipping judge for test {test_case.id} - execution status: {test_exec.status}")
            return
        
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
            
            for tool_exp in test_case.tool_expectations:
                # Check if this tool was actually called
                tool_was_called = tool_exp.name in test_exec.actual_tools
                
                arg_results = []
                for arg_assertion in tool_exp.arguments:
                    assertions = []
                    for assertion_text in arg_assertion.assertion:
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
            
            # 3. Evaluate response quality assertion if present
            response_quality = None
            response_quality_passed = True
            
            if test_case.response_quality_expectation and hasattr(test_case.response_quality_expectation, 'assertion'):
                result = await self._evaluate_single_assertion(
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
            
            # 4. Calculate overall passed status
            all_tools_called = all(tool.was_called for tool in expected_tools)
            overall_passed = all_tools_called and all_tool_assertions_passed and response_quality_passed
            
            # 5. Build final TestCaseResult
            test_exec.test_case_result = TestCaseResult(
                testcase_id=test_case.id,
                passed=overall_passed,
                response_from_agent=response_from_agent,
                expected_tools=expected_tools,
                tool_expectations=tool_expectations,
                response_quality_assertion=response_quality,
                actual_tool_calls=test_exec.tool_calls,  # Capture what agent actually did
                execution_error=None  # No execution error if we got here
            )
            
            logger.info(f"Test case {test_case.id} judged: passed={overall_passed} "
                       f"(tools: {all_tools_called}, assertions: {all_tool_assertions_passed}, quality: {response_quality_passed})")
            
        except Exception as e:
            logger.error(f"Error judging test {test_case.id}: {str(e)}")
            # Create a failed result
            test_exec.test_case_result = TestCaseResult(
                testcase_id=test_case.id,
                passed=False,
                response_from_agent=f"Judge error: {str(e)}",
                expected_tools=[],
                tool_expectations=[],
                response_quality_assertion=None,
                actual_tool_calls=test_exec.tool_calls,
                execution_error=f"Judge error: {str(e)}"
            )
    
    async def _evaluate_single_assertion(self, assertion_text, tool_name, argument_name, test_case, test_exec, assertion_type):
        """Evaluate a single assertion and return pass/fail result."""
        
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
        
        try:
            messages = [
                {"role": "system", "content": "You are a precise evaluator. Assess each assertion objectively and return ONLY valid JSON with no additional text. Keep reasoning to ONE sentence only. Return only True if the assertion is clearly satisfied."},
                {"role": "user", "content": judge_prompt}
            ]
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
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