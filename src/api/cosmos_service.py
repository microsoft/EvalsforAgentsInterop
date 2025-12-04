import asyncio
from typing import List, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
from .models import (
    Dataset, DatasetResponse, TestCaseResponse, Agent,
    TestCase, EvaluatorContract, Metadata, SeedScenario,
    ToolCallResult, McpToolLogEntry
)
from . import config


class CosmosDBService:
    def __init__(self):
        credential = config.COSMOS_KEY if config.COSMOS_KEY else DefaultAzureCredential()
        self.client = CosmosClient(config.COSMOS_ENDPOINT, credential=credential)
        self._database = None
        self._datasets_container = None
        self._testcases_container = None
        self._agents_container = None
        self._evaluations_container = None
        self._testresults_container = None
    
    async def _ensure_initialized(self):
        """Lazy initialization of database and containers (non-blocking)"""
        if self._datasets_container is None:
            # Run blocking I/O in thread pool to avoid blocking event loop
            self._database = await asyncio.to_thread(
                self.client.create_database_if_not_exists,
                config.COSMOS_DATABASE
            )
            self._datasets_container = await asyncio.to_thread(
                self._database.create_container_if_not_exists,
                id=config.COSMOS_DATASETS_CONTAINER,
                partition_key=PartitionKey(path="/id")
            )
            self._testcases_container = await asyncio.to_thread(
                self._database.create_container_if_not_exists,
                id=config.COSMOS_TESTCASES_CONTAINER,
                partition_key=PartitionKey(path="/dataset_id")
            )
            self._agents_container = await asyncio.to_thread(
                self._database.create_container_if_not_exists,
                id=config.COSMOS_AGENTS_CONTAINER,
                partition_key=PartitionKey(path="/id")
            )
            self._evaluations_container = await asyncio.to_thread(
                self._database.create_container_if_not_exists,
                id=config.COSMOS_EVALUATIONS_CONTAINER,
                partition_key=PartitionKey(path="/id")
            )

    # ===== Dataset CRUD Operations =====
    async def create_dataset_from_contract(self, contract: EvaluatorContract) -> Dataset:
        """
        Create a dataset from an EvaluatorContract.
        Stores dataset and test_cases separately in Cosmos DB.
        
        Args:
            contract: EvaluatorContract with metadata, seed, and test_cases
            
        Returns:
            Dataset with test_case_ids populated
        """
        await self._ensure_initialized()
        
        # Convert contract to dict, then to API models
        contract_dict = contract.model_dump(mode='json')
            
        # Create dataset without inline test cases
        dataset = Dataset(
            id=contract_dict['id'],
            metadata=Metadata(**contract_dict['metadata']),
            seed=SeedScenario(**contract_dict['seed']),
            test_case_ids=[],
            created_at=contract_dict.get('created_at') or contract_dict['metadata']['created_at']
        )
        
        # Store dataset
        data = dataset.model_dump(mode='json')
        item = await asyncio.to_thread(
            self._datasets_container.create_item,
            body=data
        )
        stored_dataset = Dataset(**item)
        
        # Store test cases separately
        test_case_ids = []
        for test_case in contract.test_cases:
            # Convert TestCase to dict for proper serialization
            tc_dict = test_case.model_dump(mode='json')
            tc_dict['dataset_id'] = contract_dict['id']  # Ensure dataset_id is set
            
            # Create TestCase from the dict
            api_test_case = TestCase(**tc_dict)
            
            stored_tc = await self.create_testcase(api_test_case)
            test_case_ids.append(stored_tc.id)
        
        # Update dataset with test case IDs
        stored_dataset.test_case_ids = test_case_ids
        return await self.update_dataset(stored_dataset)
    
    async def create_dataset(self, dataset_or_contract) -> Dataset:
        """
        Create a dataset from either a Dataset or EvaluatorContract.
        If EvaluatorContract is provided, test_cases are stored separately.
        """
        await self._ensure_initialized()
        
        # Handle EvaluatorContract -> separate dataset and test cases
        if isinstance(dataset_or_contract, EvaluatorContract):
            contract: EvaluatorContract = dataset_or_contract
            
            # Convert contract to dict, then to API models
            contract_dict = contract.model_dump(mode='json')            
            
            # Create dataset without inline test cases
            dataset = Dataset(
                id=contract_dict['id'],
                metadata=Metadata(**contract_dict['metadata']),
                seed=SeedScenario(**contract_dict['seed']),
                test_case_ids=[],
                created_at=contract_dict.get('created_at') or contract_dict['metadata']['created_at']
            )
            
            # Store dataset
            data = dataset.model_dump(mode='json')
            item = await asyncio.to_thread(
                self._datasets_container.create_item,
                body=data
            )
            stored_dataset = Dataset(**item)
            
            # Store test cases separately
            test_case_ids = []
            for test_case in contract.test_cases:
                # Convert TestCase to dict for proper serialization
                tc_dict = test_case.model_dump(mode='json')
                tc_dict['dataset_id'] = contract_dict['id']  # Ensure dataset_id is set
                
                # Create TestCase from the dict
                api_test_case = TestCase(**tc_dict)
                
                stored_tc = await self.create_testcase(api_test_case)
                test_case_ids.append(stored_tc.id)
            
            # Update dataset with test case IDs
            stored_dataset.test_case_ids = test_case_ids
            return await self.update_dataset(stored_dataset)
        
        # Handle regular Dataset object
        else:
            dataset: Dataset = dataset_or_contract
            data = dataset.model_dump(mode='json')
            item = await asyncio.to_thread(
                self._datasets_container.create_item,
                body=data
            )
            return Dataset(**item)
    
    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        await self._ensure_initialized()
        try:
            item = await asyncio.to_thread(
                self._datasets_container.read_item,
                item=dataset_id,
                partition_key=dataset_id
            )
            return Dataset(**item)
        except exceptions.CosmosResourceNotFoundError:
            return None
    
    async def list_datasets(self, skip: int = 0, limit: int = 100) -> List[Dataset]:
        await self._ensure_initialized()
        query = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET @skip LIMIT @limit"
        
        def _query():
            return list(self._datasets_container.query_items(
                query=query,
                parameters=[{"name": "@skip", "value": skip}, {"name": "@limit", "value": limit}],
                enable_cross_partition_query=True
            ))
        
        items = await asyncio.to_thread(_query)
        return [Dataset(**item) for item in items]
    
    async def update_dataset(self, dataset: Dataset) -> Dataset:
        """Update an existing dataset in Cosmos DB"""
        await self._ensure_initialized()
        data = dataset.model_dump(mode='json')
        item = await asyncio.to_thread(
            self._datasets_container.replace_item,
            item=dataset.id,
            body=data
        )
        return Dataset(**item)
    
    async def delete_dataset(self, dataset_id: str) -> bool:
        await self._ensure_initialized()
        try:
            # Also delete all associated test cases
            test_cases = await self.list_testcases_by_dataset(dataset_id)
            for tc in test_cases:
                await self.delete_testcase(tc.id, dataset_id)
            
            # Delete the dataset
            await asyncio.to_thread(
                self._datasets_container.delete_item,
                item=dataset_id,
                partition_key=dataset_id
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    # ===== TestCase CRUD Operations =====
    async def create_testcase(self, test_case: TestCase) -> TestCase:
        await self._ensure_initialized()
        data = test_case.model_dump(mode='json')
        item = await asyncio.to_thread(
            self._testcases_container.create_item,
            body=data
        )
        
        # Update dataset's test_case_ids array
        dataset = await self.get_dataset(test_case.dataset_id)
        if dataset:
            if test_case.id not in dataset.test_case_ids:
                dataset.test_case_ids.append(test_case.id)
                await self.update_dataset(dataset)
        
        return TestCase(**item)
    
    async def get_testcase(self, testcase_id: str, dataset_id: str) -> Optional[TestCase]:
        await self._ensure_initialized()
        try:
            item = await asyncio.to_thread(
                self._testcases_container.read_item,
                item=testcase_id,
                partition_key=dataset_id
            )
            return TestCase(**item)
        except exceptions.CosmosResourceNotFoundError:
            return None
    
    async def get_testcase_by_id(self, testcase_id: str) -> Optional[TestCase]:
        """Get a test case by ID using cross-partition query when dataset_id is unknown"""
        await self._ensure_initialized()
        query = "SELECT * FROM c WHERE c.id = @testcase_id"
        
        def _query():
            return list(self._testcases_container.query_items(
                query=query,
                parameters=[{"name": "@testcase_id", "value": testcase_id}],
                enable_cross_partition_query=True,
                max_item_count=1
            ))
        
        try:
            items = await asyncio.to_thread(_query)
            if items:
                return TestCase(**items[0])
            return None
        except Exception:
            return None
    
    async def list_testcases_by_dataset(self, dataset_id: str) -> List[TestCase]:
        await self._ensure_initialized()
        query = "SELECT * FROM c WHERE c.dataset_id = @dataset_id"
        
        def _query():
            return list(self._testcases_container.query_items(
                query=query,
                parameters=[{"name": "@dataset_id", "value": dataset_id}],
                partition_key=dataset_id
            ))
        
        items = await asyncio.to_thread(_query)
        return [TestCase(**item) for item in items]
    
    async def update_testcase(self, test_case: TestCase) -> TestCase:
        await self._ensure_initialized()
        data = test_case.model_dump(mode='json')
        item = await asyncio.to_thread(
            self._testcases_container.replace_item,
            item=test_case.id,
            body=data
        )
        return TestCase(**item)
    
    async def delete_testcase(self, testcase_id: str, dataset_id: str) -> bool:
        await self._ensure_initialized()
        try:
            await asyncio.to_thread(
                self._testcases_container.delete_item,
                item=testcase_id,
                partition_key=dataset_id
            )
            
            # Update dataset's test_case_ids array
            dataset = await self.get_dataset(dataset_id)
            if dataset and testcase_id in dataset.test_case_ids:
                dataset.test_case_ids.remove(testcase_id)
                await self.update_dataset(dataset)
            
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    # Agent methods
    async def create_agent(self, agent: Agent) -> Agent:
        await self._ensure_initialized()
        item = await asyncio.to_thread(
            self._agents_container.create_item,
            body=agent.model_dump(mode='json')
        )
        return Agent(**item)

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        await self._ensure_initialized()
        try:
            item = await asyncio.to_thread(
                self._agents_container.read_item,
                item=agent_id,
                partition_key=agent_id
            )
            return Agent(**item)
        except exceptions.CosmosResourceNotFoundError:
            return None

    async def list_agents(self, skip: int = 0, limit: int = 100) -> List[Agent]:
        await self._ensure_initialized()
        query = "SELECT * FROM c ORDER BY c.createdAt DESC OFFSET @skip LIMIT @limit"

        def _query():
            return list(self._agents_container.query_items(
                query=query,
                parameters=[{"name": "@skip", "value": skip}, {"name": "@limit", "value": limit}],
                enable_cross_partition_query=True
            ))

        items = await asyncio.to_thread(_query)
        return [Agent(**item) for item in items]

    async def update_agent(self, agent_id: str, agent: Agent) -> Agent:
        await self._ensure_initialized()
        item = await asyncio.to_thread(
            self._agents_container.replace_item,
            item=agent_id,
            body=agent.model_dump(mode='json')
        )
        return Agent(**item)

    async def delete_agent(self, agent_id: str) -> bool:
        await self._ensure_initialized()
        try:
            await asyncio.to_thread(
                self._agents_container.delete_item,
                item=agent_id,
                partition_key=agent_id
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    # Evaluation Run methods
    async def create_evaluation_run(self, evaluation_run) -> "EvaluationRun":
        await self._ensure_initialized()
        item = await asyncio.to_thread(
            self._evaluations_container.create_item,
            body=evaluation_run.model_dump(mode='json')
        )
        from .models import EvaluationRun
        return EvaluationRun(**item)

    async def get_evaluation_run(self, evaluation_id: str) -> Optional["EvaluationRun"]:
        await self._ensure_initialized()
        try:
            item = await asyncio.to_thread(
                self._evaluations_container.read_item,
                item=evaluation_id,
                partition_key=evaluation_id
            )
            from .models import EvaluationRun
            return EvaluationRun(**item)
        except exceptions.CosmosResourceNotFoundError:
            return None

    async def list_evaluation_runs(self, skip: int = 0, limit: int = 100, agent_id: Optional[str] = None) -> List["EvaluationRun"]:
        await self._ensure_initialized()
        
        # Build query with optional agent_id filter
        if agent_id:
            query = "SELECT * FROM c WHERE c.agent_id = @agent_id ORDER BY c.created_at DESC OFFSET @skip LIMIT @limit"
            parameters = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@skip", "value": skip},
                {"name": "@limit", "value": limit}
            ]
        else:
            query = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET @skip LIMIT @limit"
            parameters = [
                {"name": "@skip", "value": skip},
                {"name": "@limit", "value": limit}
            ]
        
        def _query():
            return list(self._evaluations_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
        
        items = await asyncio.to_thread(_query)
        from .models import EvaluationRun
        return [EvaluationRun(**item) for item in items]

    async def update_evaluation_run(self, evaluation_run) -> "EvaluationRun":
        await self._ensure_initialized()
        
        # Convert evaluation run to dict
        eval_dict = evaluation_run.model_dump(mode='json')
        
        # Convert test results to database format
        if 'test_results' in eval_dict:
            converted_results = []
            for test_result in evaluation_run.test_results:
                if hasattr(test_result, 'to_database_format'):
                    converted_results.append(test_result.to_database_format())
                else:
                    # Fallback for older format
                    converted_results.append(test_result.model_dump(mode='json'))
            eval_dict['test_results'] = converted_results
        
        item = await asyncio.to_thread(
            self._evaluations_container.replace_item,
            item=evaluation_run.id,
            body=eval_dict
        )
        from .models import EvaluationRun
        return EvaluationRun(**item)

    async def delete_evaluation_run(self, evaluation_id: str) -> bool:
        await self._ensure_initialized()
        try:
            await asyncio.to_thread(
                self._evaluations_container.delete_item,
                item=evaluation_id,
                partition_key=evaluation_id
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

#===== MCP Logging and retrieval services =====

    async def log_tool_call(self, correlation_id: str, testcase_id: str, tool_name: str, parameters: dict, response: "ToolCallResult") -> None:
        """
        Log a tool call and its response to CosmosDB
        
        Args:
            service: The CosmosDBService instance to use for logging
            correlation_id: The run ID
            testcase_id: The test case ID to log the tool call under
            tool_name: Name of the tool that was called
            parameters: Parameters passed to the tool (can be any object)
            response: Response from the tool (can be any object, including ToolCallResult)
        """

        log_entry = McpToolLogEntry(tool_name=tool_name,input_parameters=parameters,result=response).model_dump_json()
                
        if self._evaluations_container is not None:
            # Use CosmosDB logging
            try:
                    # Try to read existing document
                    existing_doc = self._evaluations_container.read_item(
                        item=correlation_id,
                        partition_key=correlation_id
                    )
                    
                    # Find the specific test case within the document
                    test_cases = existing_doc.get("test_cases", [])
                    testcase_found = False
                    
                    for test_case in test_cases:
                        if test_case.get("testcase_id") == testcase_id:
                            # Append to existing actualToolCalls for this test case
                            if "actualToolCalls" not in test_case:
                                test_case["actualToolCalls"] = []
                            test_case["actualToolCalls"].append(log_entry)
                            testcase_found = True
                            break
                    
                    if not testcase_found:
                        raise ValueError(f"Test case with ID {testcase_id} not found in evaluation run {correlation_id}")
                    
                    # Update the document
                    self._evaluations_container.replace_item(
                        item=correlation_id,
                        body=existing_doc
                    )
                    
            except exceptions.CosmosResourceNotFoundError:
                raise ValueError(f"Evaluation run with ID {correlation_id} not found for logging.")
            except exceptions.CosmosHttpResponseError as e:
                raise ConnectionError(f"Failed to log tool call to CosmosDB: {e}")
            except Exception as e:
                raise RuntimeError(f"Unexpected error during logging to CosmosDB: {e}")



_service: Optional[CosmosDBService] = None

def get_cosmos_service() -> CosmosDBService:
    global _service
    if not _service:
        _service = CosmosDBService()
    return _service

async def log_mcp_tool_call(correlation_id: str, testcase_id: str, tool_name: str, parameters: dict, response: "ToolCallResult") -> None:
    """
    Global function to log MCP tool calls using the default cosmos service
    
    Args:
        correlation_id: The run ID
        testcase_id: The test case ID to log the tool call under
        tool_name: Name of the tool that was called
        parameters: Parameters passed to the tool
        response: Response from the tool
    """
    service = get_cosmos_service()
    await service._ensure_initialized()
    #await service.log_tool_call(correlation_id, testcase_id, tool_name, parameters, response)
