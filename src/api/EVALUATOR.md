# Evaluator Service

The Evaluator Service provides async evaluation capabilities for testing AI agents against evaluation datasets.

## Features

- **Async Execution**: Runs evaluations asynchronously (5-10 minutes typical runtime)
- **Sequential Test Processing**: Processes one test at a time to avoid overwhelming agents
- **Agent Integration**: Calls agent endpoints with configurable authentication
- **LLM Judging**: Uses Azure OpenAI to evaluate agent responses
- **Progress Tracking**: Real-time status updates and progress monitoring
- **Tool Call Logging**: Captures and analyzes tool usage patterns

## API Endpoints

### Create Evaluation
```http
POST /api/evaluations
```

**Request Body:**
```json
{
  "name": "Customer Service Agent Evaluation",
  "dataset_id": "seed_1729512000.123",
  "agent_id": "agent_1729512000.456", 
  "agent_endpoint": "https://your-agent.azurewebsites.net/chat",
  "agent_auth_required": true,
  "timeout_seconds": 300
}
}
```

**Response:**
```json
{
  "id": "eval_1729512000.789",
  "name": "Customer Service Agent Evaluation",
  "status": "pending",
  "total_tests": 5,
  "completed_tests": 0,
  "created_at": "2025-10-30T10:00:00Z"
}
```

### Get Evaluation Status
```http
GET /api/evaluations/{evaluation_id}
```

**Response:**
```json
{
  "id": "eval_1729512000.789",
  "name": "Customer Service Agent Evaluation", 
  "status": "running",
  "total_tests": 5,
  "completed_tests": 3,
  "failed_tests": 0,
  "average_score": 0.85,
  "total_execution_time_ms": 45000,
  "started_at": "2025-10-30T10:00:01Z"
}
```

### Get Test Results
```http
GET /api/evaluations/{evaluation_id}/results
```

**Response:**
```json
[
  {
    "id": "result_1729512000.101",
    "test_case_id": "tc_1729512000.111",
    "input": "I forgot my password",
    "expected_tools": ["sendEmail", "resetPassword"],
    "agent_output": "I'll help you reset your password...",
    "actual_tools": ["sendEmail", "resetPassword"],
    "execution_status": "completed",
    "execution_time_ms": 1500,
    "judge_score": 0.9,
    "judge_feedback": "Excellent response with correct tool usage",
    "tool_calls": [
      {
        "tool": "sendEmail",
        "args": {"recipient": "user@example.com", "subject": "Password Reset"}
      }
    ]
  }
]
```

## Agent Endpoint Requirements

Your agent endpoint should accept POST requests with this format:

**Request:**
```json
{
  "input": "User message or scenario input",
  "test_id": "result_1729512000.101", 
  "evaluation_run_id": "eval_1729512000.789"
}
```

**Response:**
```json
{
  "output": "Agent's response text",
  "tool_calls": ["tool1", "tool2"], 
  "tool_call_details": [
    {
      "tool": "sendEmail",
      "args": {"recipient": "user@example.com"},
      "result": "Email sent successfully"
    }
  ]
}
```

## Authentication

### Azure AD (Recommended)
When `agent_auth_required: true`, the evaluator will include an Azure AD bearer token:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...
```

### Unauthenticated
Set `agent_auth_required: false` for endpoints that don't require authentication.

## Evaluation Flow

1. **Create Evaluation**: POST to `/api/evaluations` with dataset and agent info
2. **Background Processing**: Evaluation starts automatically in background
3. **Sequential Testing**: Each test case is processed one at a time:
   - Create test result record with input
   - Call agent endpoint with auth if required  
   - Wait for agent response
   - Update test result with agent output
   - Run LLM judge against test case and result
   - Update progress counters
4. **Completion**: Final scores calculated and status set to "completed"

## Example Usage

```python
import httpx
import asyncio

async def run_evaluation():
    async with httpx.AsyncClient() as client:
        # Create evaluation
        eval_request = {
            "name": "My Agent Test",
            "dataset_id": "seed_123",
            "agent_id": "agent_456",
            "agent_endpoint": "https://my-agent.com/chat",
            "agent_auth_required": True
        }
        
        response = await client.post(
            "http://localhost:8000/api/evaluations",
            json=eval_request
        )
        evaluation = response.json()
        evaluation_id = evaluation["id"]
        
        # Poll for completion
        while True:
            response = await client.get(f"http://localhost:8000/api/evaluations/{evaluation_id}")
            eval_status = response.json()
            
            if eval_status["status"] == "completed":
                print(f"Evaluation completed! Average score: {eval_status['average_score']}")
                break
            elif eval_status["status"] == "failed":
                print("Evaluation failed!")
                break
            else:
                print(f"Progress: {eval_status['completed_tests']}/{eval_status['total_tests']}")
                await asyncio.sleep(10)

# Run the evaluation
asyncio.run(run_evaluation())
```

## Error Handling

The evaluator handles various error scenarios:

- **Agent Timeout**: Configurable timeout per test (default 300s)
- **Agent Errors**: HTTP errors are logged, test marked as failed
- **Judge Failures**: LLM judge errors are captured, test continues
- **Network Issues**: Retries and proper error logging

## Monitoring

All evaluation activities are logged with structured logging:
- Test execution timing
- Agent response analysis  
- Judge scoring details
- Error conditions and recovery

Check the API logs for detailed evaluation traces.