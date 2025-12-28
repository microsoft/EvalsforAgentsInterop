# Evals for Agent Interop API

Lightweight FastAPI backend for test case management and agent evaluation.

## Files

```
config.py            # Loads environment variables
main.py              # FastAPI app
controllers.py       # API endpoints
models.py            # Pydantic data models
cosmos_service.py    # Cosmos DB layer
evaluator_service.py # Agent evaluation system
cosmos_preload.py    # Load evaluation datasets to Cosmos DB
```

## API Endpoints

### Datasets

- `POST /api/datasets` - Create dataset
- `GET /api/datasets` - List datasets (paginated)
- `GET /api/datasets/{id}` - Get dataset
- `DELETE /api/datasets/{id}` - Delete dataset

### Test Cases

- `POST /api/datasets/{id}/testcases` - Add test case
- `GET /api/datasets/{id}/testcases` - List test cases
- `GET /api/datasets/{id}/testcases/{tc_id}` - Get test case
- `DELETE /api/datasets/{id}/testcases/{tc_id}` - Delete test case

### Agents

- `POST /api/agents` - Add agent registration
- `GET /api/agents` - List agents
- `GET /api/agents/{id}` - Get agent details
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent

### Evaluations

- `POST /api/evaluations` - Create evaluation run
- `GET /api/evaluations` - List evaluation runs
- `GET /api/evaluations/{id}` - Get evaluation run
- `GET /api/evaluations/{id}/results` - Get evaluation results
- `GET /api/evaluations/{id}/results/{result_id}` - Get specific test result
- `POST /api/evaluations/{id}/cancel` - Cancel a running evaluation
- `DELETE /api/evaluations/{id}` - Delete an evaluation

### Streaming

- `GET /api/evaluations/{id}/stream` - SSE stream for real-time evaluation progress updates

## Features

### Rate Limiting
The evaluation service implements rate limiting with automatic retry logic when calling the agent endpoint. If a 429 (Too Many Requests) response is received:
- Automatic retry with exponential backoff
- Retry count tracked per test case result
- Configurable through environment variables

### Streaming Progress Updates
Real-time evaluation progress is available via Server-Sent Events (SSE):
- Connect to `/api/evaluations/{id}/stream` for live updates
- Events include test case completion, scores, and status changes
- Automatic reconnection support in the webapp

## Data Models

**Dataset**

```json
{
  "id": "dataset_1729512000123",
  "metadata": {
    "generator_id": "gen_1729512000123",
    "suite_id": "suite_1729512000123", 
    "created_at": "2025-10-21T10:00:00Z",
    "version": "1.0",
    "schema_hash": ""
  },
  "seed": {
    "name": "Customer Support Scenarios",
    "goal": "Help customer with password reset",
    "input": {"num_test_cases": 5}
  },
  "test_case_ids": ["tc_001", "tc_002"],
  "created_at": "2025-10-21T10:00:00Z"
}
```

**TestCase**

```json
{
  "id": "tc_1729512100456",
  "dataset_id": "dataset_1729512000123",
  "description": "Password reset request",
  "input": "I forgot my password",
  "minimal_tool_set": ["sendEmail", "resetPassword"],
  "tool_expectations": [
    {
      "name": "sendEmail",
      "arguments": [
        {
          "name": "recipient", 
          "assertion": "Should be user's email address",
          "rubrics": []
        }
      ]
    }
  ],
  "expected_response": "I'll send you a password reset email",
  "response_quality_expectation": {
    "assertion": "Response should be helpful and clear",
    "rubrics": []
  },
  "references_seed": {}
}
```

**Agent**

```json
{
  "id": "agent_1761764132.513426",
  "name": "Customer Support Agent",
  "description": "Help customers with any technical issues related to their user accounts",
  "model": "gpt-4o",
  "agent_invocation_url": "http://test-endpoint/invoke",
  "createdAt": "2025-10-20T10:00:00Z"
}
```

## Quick Start

### Prerequisites

1. **Azure Cosmos DB**: NoSQL API account
2. **Azure OpenAI**: GPT 4.1 deployment for LLM test judge
3. **Azure Authentication**: Run `az login` for DefaultAzureCredential

### Environment Setup

```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Edit .env with your credentials
nano .env  # or use your preferred editor
```

The API uses the consolidated `.env` file at the repo root. Required environment variables:

```bash
# Cosmos DB (used by API)
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-key-here
COSMOS_DATABASE_NAME=interopevals
COSMOS_DATASETS_CONTAINER_NAME=datasets
COSMOS_TESTCASES_CONTAINER_NAME=testcases
COSMOS_AGENTS_CONTAINER_NAME=agents

# Azure OpenAI (shared with Agent)
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Load Sample Data

```bash
# From src/api directory
python cosmos_preload.py --dry-run  # Preview what will be uploaded
python cosmos_preload.py           # Upload sample datasets
python cosmos_preload.py --force   # Overwrite existing data
```

### Run with Docker

```bash
# From repo root
docker-compose up

# The API will be available at http://localhost:8000
```

### Run Locally (Python)

```bash
# Install dependencies (from repo root)
pip install -r src/api/requirements.txt

# Run the server (from repo root)
python -m src.api.main

# The API will be available at http://localhost:8000
```

## Interactive Docs

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Azure Deployment

```bash
# Create App Service
az webapp create --resource-group <rg> --plan <plan> \
  --name <app-name> --runtime "PYTHON:3.11"

# Set environment variables
az webapp config appsettings set --name <app-name> --resource-group <rg> \
  --settings COSMOS_ENDPOINT=<endpoint> COSMOS_DATABASE_NAME=interopevals 

# Enable managed identity (for production, no COSMOS_KEY needed)
az webapp identity assign --name <app-name> --resource-group <rg>

# Deploy
az webapp up --name <app-name> --resource-group <rg>
```

## Testing

The API includes a comprehensive test suite with unit tests, integration tests, and mock services.

### Install Test Dependencies

```bash
# From repo root
pip install -r requirements-test.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/api --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and mock services
├── unit/
│   ├── test_controllers.py  # API endpoint tests
│   └── test_models.py       # Data model validation tests
├── integration/
│   └── test_evaluation_flow.py  # End-to-end evaluation tests
└── mocks/
    └── mock_agent_server.py # Mock agent for testing
```

---
