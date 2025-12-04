from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks, Body
from datetime import datetime, timezone

from .models import (
    Dataset,
    DatasetResponse,
    TestCaseResponse,
    Metadata,
    SeedScenario,
    TestCase,
    TestCaseCreate,
    CreateDatasetRequest,
    Agent, 
    AgentCreate,
    EvaluationRun,
    EvaluationRunCreate,
    TestCaseResult
)
from .cosmos_service import get_cosmos_service
from .evaluator_service import get_evaluator_service

router = APIRouter(prefix="/api")
db = get_cosmos_service()
evaluator = get_evaluator_service(db)


# Evaluation Datasets
@router.post("/datasets", response_model=DatasetResponse, status_code=201)
async def create_dataset(request: CreateDatasetRequest):
    """Create a new evaluation dataset with auto-generated IDs and timestamps
    
    Only requires: name, goal, and optionally input/schema_hash
    All IDs (generator_id, suite_id) and timestamps are auto-generated
    """
    try:
        # Create dataset (without test cases)
        dataset = Dataset(
            metadata=Metadata(schema_hash=request.schema_hash),
            seed=SeedScenario(
                name=request.name,
                goal=request.goal,
                input=request.input
            ),
            test_case_ids=[]
        )
        saved_dataset = await db.create_dataset(dataset)
        
        # Return as DatasetResponse
        return DatasetResponse(
            id=saved_dataset.id,
            metadata=saved_dataset.metadata,
            seed=saved_dataset.seed,
            test_case_ids=saved_dataset.test_case_ids,
            created_at=saved_dataset.created_at
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to create dataset: {str(e)}")


@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(skip: int = 0, limit: int = 100):
    datasets = await db.list_datasets(skip=skip, limit=limit)
    return [DatasetResponse(
        id=d.id,
        metadata=d.metadata,
        seed=d.seed,
        test_case_ids=d.test_case_ids,
        created_at=d.created_at
    ) for d in datasets]


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    return DatasetResponse(
        id=dataset.id,
        metadata=dataset.metadata,
        seed=dataset.seed,
        test_case_ids=dataset.test_case_ids,
        created_at=dataset.created_at
    )


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str):
    if not await db.delete_dataset(dataset_id):
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")


# Test Cases
@router.post("/datasets/{dataset_id}/testcases", response_model=TestCaseResponse, status_code=201)
async def add_testcase(dataset_id: str, testcase: TestCaseCreate):
    """Add a new test case to an existing dataset
    
    The test case ID is auto-generated and dataset_id is automatically set from the URL
    """
    # Verify dataset exists
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    
    # Create TestCase with auto-generated ID and dataset_id from URL
    new_tc = TestCase(
        dataset_id=dataset_id,  # Use dataset_id from URL
        name=testcase.name,
        description=testcase.description,
        input=testcase.input,
        minimal_tool_set=testcase.minimal_tool_set,
        tool_expectations=testcase.tool_expectations,
        expected_response=testcase.expected_response,
        response_quality_expectation=testcase.response_quality_expectation,
        references_seed=testcase.references_seed
    )
    
    # Create test case in testcases container (auto-updates dataset.test_case_ids)
    created_tc = await db.create_testcase(new_tc)
    
    # Return the created test case
    return TestCaseResponse(
        id=created_tc.id,
        dataset_id=created_tc.dataset_id,
        name=created_tc.name,
        description=created_tc.description,
        input=created_tc.input,
        minimal_tool_set=created_tc.minimal_tool_set,
        tool_expectations=created_tc.tool_expectations,
        expected_response=created_tc.expected_response,
        response_quality_expectation=created_tc.response_quality_expectation,
        references_seed=created_tc.references_seed
    )


@router.get("/datasets/{dataset_id}/testcases", response_model=List[TestCaseResponse])
async def list_testcases(dataset_id: str):
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    testcases = await db.list_testcases_by_dataset(dataset_id)
    return [TestCaseResponse(
        id=tc.id,
        dataset_id=tc.dataset_id,
        name=tc.name or tc.id,  # Use id if name is None or empty
        description=tc.description,
        input=tc.input,
        minimal_tool_set=tc.minimal_tool_set,
        tool_expectations=tc.tool_expectations,
        expected_response=tc.expected_response,
        response_quality_expectation=tc.response_quality_expectation,
        references_seed=tc.references_seed
    ) for tc in testcases]


@router.get("/datasets/{dataset_id}/testcases/{tc_id}", response_model=TestCaseResponse)
async def get_testcase(dataset_id: str, tc_id: str):
    tc = await db.get_testcase(tc_id, dataset_id)
    if not tc:
        raise HTTPException(404, f"Test case '{tc_id}' not found")
    return TestCaseResponse(
        id=tc.id,
        dataset_id=tc.dataset_id,
        name=tc.name,
        description=tc.description,
        input=tc.input,
        minimal_tool_set=tc.minimal_tool_set,
        tool_expectations=tc.tool_expectations,
        expected_response=tc.expected_response,
        response_quality_expectation=tc.response_quality_expectation,
        references_seed=tc.references_seed
    )


@router.put("/datasets/{dataset_id}/testcases/{tc_id}", response_model=TestCaseResponse)
async def update_testcase(dataset_id: str, tc_id: str, testcase_data: TestCaseCreate):
    """Update an existing test case
    
    Updates all fields of an existing test case. The test case ID and dataset_id cannot be changed.
    """
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    
    existing_tc = await db.get_testcase(tc_id, dataset_id)
    if not existing_tc:
        raise HTTPException(404, f"Test case '{tc_id}' not found")
    
    updated_tc = TestCase(
        id=tc_id,  # Keep existing ID
        dataset_id=dataset_id,  # Keep existing dataset_id
        name=testcase_data.name,
        description=testcase_data.description,
        input=testcase_data.input,
        minimal_tool_set=testcase_data.minimal_tool_set,
        tool_expectations=testcase_data.tool_expectations,
        expected_response=testcase_data.expected_response,
        response_quality_expectation=testcase_data.response_quality_expectation,
        references_seed=testcase_data.references_seed
    )
    
    updated_tc = await db.update_testcase(updated_tc)
    
    return TestCaseResponse(
        id=updated_tc.id,
        dataset_id=updated_tc.dataset_id,
        name=updated_tc.name,
        description=updated_tc.description,
        input=updated_tc.input,
        minimal_tool_set=updated_tc.minimal_tool_set,
        tool_expectations=updated_tc.tool_expectations,
        expected_response=updated_tc.expected_response,
        response_quality_expectation=updated_tc.response_quality_expectation,
        references_seed=updated_tc.references_seed
    )


@router.delete("/datasets/{dataset_id}/testcases/{tc_id}", status_code=204)
async def delete_testcase(dataset_id: str, tc_id: str):
    if not await db.delete_testcase(tc_id, dataset_id):
        raise HTTPException(404, f"Test case '{tc_id}' not found")

    
# Agents
@router.post("/agents", response_model=Agent, status_code=201)
async def create_agent(agent: AgentCreate):
    new_agent = Agent(name=agent.name, description=agent.description, model=agent.model, agent_invocation_url=agent.agent_invocation_url)
    return await db.create_agent(new_agent)


@router.get("/agents", response_model=List[Agent])
async def list_agents(skip: int = 0, limit: int = 100):
    return await db.list_agents(skip=skip, limit=limit)


@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    agent = await db.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return agent

@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent: AgentCreate):
    existing_agent = await db.get_agent(agent_id)
    if not existing_agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    updated_agent = Agent(
        id=existing_agent.id,
        name=agent.name,
        description=agent.description,
        model=agent.model,
        agent_invocation_url=agent.agent_invocation_url,
        createdAt=existing_agent.createdAt
    )
    return await db.update_agent(agent_id, updated_agent)

@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    if not await db.delete_agent(agent_id):
        raise HTTPException(404, f"Agent '{agent_id}' not found")


# Evaluations
@router.post("/evaluations", response_model=EvaluationRun, status_code=201)
async def create_evaluation(eval_request: EvaluationRunCreate, background_tasks: BackgroundTasks):
    
    try:
        # Create the evaluation run
        eval_run = await evaluator.create_evaluation_run(eval_request)
        
        # Start evaluation in background
        background_tasks.add_task(evaluator.start_evaluation, eval_run.id)
        
        return eval_run
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to create evaluation: {str(e)}")


@router.get("/evaluations", response_model=List[EvaluationRun])
async def list_evaluations(skip: int = 0, limit: int = 100, agent_id: Optional[str] = None):
    eval_runs = await evaluator.list_evaluation_runs(skip=skip, limit=limit, agent_id=agent_id)
    return eval_runs


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationRun)
async def get_evaluation(evaluation_id: str):
    eval_run = await evaluator.get_evaluation_run(evaluation_id)
    if not eval_run:
        raise HTTPException(404, f"Evaluation '{evaluation_id}' not found")
    return eval_run


@router.get("/evaluations/{evaluation_id}/results", response_model=List[TestCaseResult])
async def get_evaluation_results(evaluation_id: str):
    eval_run = await evaluator.get_evaluation_run(evaluation_id)
    if not eval_run:
        raise HTTPException(404, f"Evaluation '{evaluation_id}' not found")
    return eval_run.test_cases


@router.get("/evaluations/{evaluation_id}/results/{testcase_id}", response_model=TestCaseResult)
async def get_test_result(evaluation_id: str, testcase_id: str):
    eval_run = await evaluator.get_evaluation_run(evaluation_id)
    if not eval_run:
        raise HTTPException(404, f"Evaluation '{evaluation_id}' not found")
    
    # Find the specific test result
    test_result = next((tc for tc in eval_run.test_cases if tc.testcase_id == testcase_id), None)
    if not test_result:
        raise HTTPException(404, f"Test result for '{testcase_id}' not found")
    
    return test_result


@router.delete("/evaluations/{evaluation_id}", status_code=204)
async def delete_evaluation(evaluation_id: str):
    try:
        success = await evaluator.delete_evaluation_run(evaluation_id)
        if not success:
            raise HTTPException(404, f"Evaluation '{evaluation_id}' not found")
    except Exception as e:
        raise HTTPException(500, f"Failed to delete evaluation: {str(e)}")