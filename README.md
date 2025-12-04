# Evals for Agent Interop

A comprehensive platform for testing and evaluating AI agents.

## 🏗️ Architecture

Evals for Agent Interop consists of three main components:

### 1. **API (Backend)** - Port 8000
FastAPI backend that provides:
- Test case dataset management
- Agent registration and evaluation
- MCP (Model Context Protocol) server for tool execution
- Cosmos DB integration for data persistence

### 2. **Agent** - Port 8001
Sample AI agent implementation that:
- Connects to the API's MCP server for tool access
- Uses Azure OpenAI for intelligent task execution
- Demonstrates calendar scheduling and email capabilities
- Serves as a reference implementation for agent development

### 3. **Webapp (Frontend)** - Port 5000
React-based web interface for:
- Creating and managing test datasets
- Registering and configuring agents
- Running evaluations
- Viewing test results and metrics

## ☁️ Azure Infrastructure Setup

### Deploy Azure Resources

Evals for Agent Interop requires Azure Cosmos DB and Azure OpenAI resources. Use the provided Bicep template to deploy them:

```bash
cd infra

# Deploy infrastructure (Bash)
./deploy.sh

# Or using PowerShell (Windows)
.\deploy.ps1

# Or manually with Azure CLI
az deployment group create \
  --resource-group evals-interop-dev-rg \
  --template-file main.bicep \
  --parameters @main.parameters.json
```

**What gets deployed:**
- **Azure Cosmos DB** (Serverless) with containers for datasets, testcases, agents, evaluations
- **Azure Foundry** resource for hosting LLMs. You will need to manually deploy GPT 4.1 in the Azure Foundry Portal. 

**After deployment:**
1. Manually deploy GPT 4.1 in the Azure Foundry portal
2. Copy the output values from the deployment script to your `.env` file at the root of the repository

**For detailed infrastructure information, deployment options, and troubleshooting, see [infra/README.md](infra/README.md).**

### Infrastructure Files
- `infra/main.bicep` - Main infrastructure template
- `infra/main.parameters.json` - Deployment parameters
- `infra/deploy.sh` - Automated deployment script (Bash)
- `infra/deploy.ps1` - Automated deployment script (PowerShell)
- `infra/README.md` - Detailed infrastructure documentation

## 🚀 Local Development

### Prerequisites
- Azure OpenAI API credentials (from infrastructure deployment)
- Azure Cosmos DB instance (from infrastructure deployment)
- Docker Desktop installed and running (for Docker-based development)

### 1. Configure Environment Variables

Create a single `.env` file at the repo root from the provided example:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Azure credentials
nano .env
```

**Required Configuration:**
- `.env`: Contains all configuration for both API and Agent services
- Azure OpenAI credentials (shared by both services)
- Cosmos DB credentials (used by API)
- MCP server URL (used by Agent)

### 2. Install Dependencies

**Optional: Create a virtual environment**

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate

# Activate virtual environment (Windows)
.venv\Scripts\activate
```

**Install required packages:**

```bash
pip install -r src/api/requirements.txt
pip install -r src/agents/requirements.txt
```

### 3. Load Sample Data (Optional)

Upload sample datasets to Cosmos DB:

```bash
cd src/api
python cosmos_preload.py
```

### 4. Run Services Locally

#### Option A: Run Locally Without Docker

**💡 Tip**: Use VS Code launch profiles for easy debugging! The workspace includes pre-configured launch profiles in `.vscode/launch.json`:

- **API** - Runs the FastAPI backend on port 8000 with hot reload enabled
- **Agent** - Runs the sample agent server on port 8001 with hot reload enabled  
- **WebApp** - Runs the React frontend development server on port 5000
- **API + Agent + WebApp** - Compound configuration that starts all three services simultaneously

To use: Open the Run and Debug panel (Ctrl+Shift+D), select a profile, and press F5 to start debugging.

**Manual Setup (if not using launch profiles):**

**API**
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Agent**
```bash
python -m uvicorn src.agents.agent_server:app --host 0.0.0.0 --port 8001 --reload
```

**Webapp**
```bash
cd src/webapp
npm install
npm run dev
```

#### Option B: Run with Docker

**Build and Start All Services**

```bash
docker-compose up --build
```

First build takes 5-10 minutes. Subsequent builds are much faster (seconds to minutes).

**🐳 Docker Networking Notes**

The `.env` file is configured for local development. When running in Docker, services communicate using Docker service names:

- **Service-to-Service Communication**: 
  - Agent connects to API using `http://api:8000/mcp` (Docker service name)
  - Agent registration uses `http://agent:8001/agents/calendar/invoke` (Docker service name)
  - Inter-service URLs use container names: `api`, `agent`, `webapp`
- **Host Access** (from your browser/tools):
  - API: `http://localhost:8000` 
  - Agent: `http://localhost:8001`
  - WebApp: `http://localhost:5000`
- **Environment Overrides**: The `MCP_SERVER_URL` is automatically overridden in docker-compose.yml for container networking

**Development Workflow**

```bash
# Start all services
docker-compose up

# Rebuild specific service after code changes
docker-compose build api
docker-compose build agent
docker-compose build webapp

# View logs for a specific service
docker-compose logs -f api

# Stop all services
docker-compose down
```

### 5. Access the Application

- **Frontend**: http://localhost:5000
- **API Docs**: http://localhost:8000/api/docs
- **Agent Invoke**: http://localhost:8001/agents/calendar/invoke

## 📁 Project Structure

```
evals-for-agent-interop/
├── .env                  # Consolidated configuration for all services
├── .env.example          # Configuration template
├── src/
│   ├── api/              # Backend API service
│   │   └── requirements.txt
│   ├── agents/           # Sample agent implementation
│   │   ├── agent_server.py
│   │   └── requirements.txt
│   └── webapp/           # React frontend
│       └── src/
├── docker-compose.yml    # Multi-service orchestration
├── Dockerfile.api        # API container definition
├── Dockerfile.agent      # Agent container definition
└── Dockerfile.webapp     # Webapp container definition
```

## 🤖 Evaluating Your Own Agent

To integrate your own agent with the evaluation platform, your agent must expose an unauthenticated HTTP POST endpoint that conforms to the following specification.

### Endpoint

**Method**: POST

Your agent can use any endpoint path (e.g., `/invoke`, `/agents/calendar/invoke`, `/api/v1/execute`). You'll register this endpoint URL when configuring your agent in the platform.

### Request Format

```json
{
  "dataset_id": "string",
  "test_case_id": "string",
  "agent_id": "string",
  "evaluation_run_id": "string",
  "input": "string"
}
```

### Response Format

Your agent must return a JSON response with the following structure:

```json
{
  "response": "string",
  "tool_calls": [
    {
      "name": "string",
      "arguments": [
        {
          "name": "string",
          "value": "any"
        }
      ]
    }
  ]
}
```

**Fields:**
- `response` (string, required): The agent's natural language response to the user's request
- `tool_calls` (array, required): List of tools the agent invoked during execution
  - `name` (string): The name of the tool that was called
  - `arguments` (array): List of arguments passed to the tool
    - `name` (string): The parameter name
    - `value` (any): The parameter value

**Example Response:**

```json
{
  "response": "I've scheduled a 1-hour meeting with alice@company.com and bob@company.com for tomorrow at 2pm to discuss Q4 planning.",
  "tool_calls": [
    {
      "name": "mcp_CalendarTools_graph_createEvent",
      "arguments": [
        {"name": "subject", "value": "Q4 Planning Meeting"},
        {"name": "start", "value": "2025-11-05T14:00:00"},
        {"name": "end", "value": "2025-11-05T15:00:00"},
        {"name": "attendees", "value": ["alice@company.com", "bob@company.com"]}
      ]
    }
  ]
}
```

See [src/agents/agent_server.py](src/agents/agent_server.py) for a reference implementation.

## 📚 Documentation

- [API Documentation](src/api/README.md) - Detailed API endpoints and usage
- [Agent Documentation](src/agents/README.md) - Agent implementation guide
- [Evaluator Guide](src/api/EVALUATOR.md) - Evaluation system details
- [Frontend Documentation](src/webapp/README.md) - Webapp development guide

## 🔧 Troubleshooting

### Docker Compose Build Errors

**Error: Host version does not match binary version**

```
✘ [ERROR] Cannot start service: Host version "0.25.11" does not match binary version "0.25.12"
```

**Solution:**
This error occurs when there's a mismatch between the Vite versions. To fix:

1. Navigate to the webapp folder:
   ```bash
   cd src/webapp
   ```

2. Delete the `node_modules` directory:
   ```bash
   rm -rf node_modules
   ```

3. Reinstall dependencies:
   ```bash
   npm install
   ```

4. Return to the root directory and rebuild the webapp:
   ```bash
   cd ../..
   docker-compose build --no-cache webapp
   docker-compose up
   ```

### Throttling / Rate Limiting During Evaluations

If you experience throttling or rate limiting errors when running evaluations with many test cases, you can reduce the number of concurrent tests by setting the `MAX_CONCURRENT_TESTS` environment variable in your `.env` file:

```bash
# Reduce concurrent tests to avoid rate limiting (default is 5)
MAX_CONCURRENT_TESTS=2
```

Lower values reduce the load on external services (such as Azure OpenAI or your agent endpoint) at the cost of longer evaluation times.

## 🔐 Security

See [SECURITY.md](SECURITY.md) for security policies and vulnerability reporting.

## 📝 License

See [LICENSE](LICENSE) for license information.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow Microsoft's Trademark & Brand Guidelines(https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party's policies.
