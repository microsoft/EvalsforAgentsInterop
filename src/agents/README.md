# Calendar Agent

Azure OpenAI-powered agent that uses MCP (Model Context Protocol) for tool execution.

## 🚀 Quick Start

### With Docker (Recommended)

```bash
# From repo root
docker-compose up

# Agent will be available at http://localhost:8001
```

### Locally

```bash
# 1. Copy environment file (from repo root)
cp .env.example .env

# 2. Edit .env with your credentials
nano .env

# 3. Install dependencies (from repo root)
pip install -r src/agents/requirements.txt

# 4. Run the agent (from repo root)
python -m uvicorn src.agents.agent_server:app --port 8001

# Agent will be available at http://localhost:8001
```

## ⚙️ Configuration

The agent uses the consolidated `.env` file at the repo root. Create it from `.env.example`:

```bash
# From repo root
cp .env.example .env
nano .env
```

Key configuration variables the agent uses:

```bash
# MCP Server URL (automatically adjusted for Docker vs local)
MCP_SERVER_URL=http://localhost:8000/mcp

# Azure OpenAI (shared with API service)
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

**Docker Networking:**
- The `MCP_SERVER_URL` is automatically overridden to `http://api:8000/mcp` in docker-compose.yml

**Authentication:**
- **Docker**: Uses API key authentication (required)
- **Local Dev**: Supports both API key and DefaultAzureCredential (az login)

## 📞 Invoke the Agent

```bash
curl -X POST http://localhost:8001/agents/calendar/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "dataset_123",
    "test_case_id": "tc_001",
    "agent_id": "calendar_agent",
    "evaluation_run_id": "run_456",
    "input": "Schedule a 1-hour meeting with alice@company.com and bob@company.com tomorrow at 2pm to discuss Q4 planning"
  }'
```

## 🔗 MCP Server Connection

The agent connects to the API's MCP server to discover and execute tools dynamically.

**On startup, the agent will:**
1. Connect to the MCP server via streamable HTTP
2. Discover available tools dynamically from the server
3. Use only the tools provided by the MCP server
4. **No fallback** - tools are only available if MCP is connected

## 🛠 Tools

Tools are **dynamically discovered** from your MCP server. The agent has no hardcoded tools.

Example tools from an MCP server:
- `mcp_CalendarTools_graph_createEvent` - Create calendar events
- `mcp_CalendarTools_graph_listEvents` - List calendar events  
- `mcp_CalendarTools_graph_listUsers` - List users
- `searchMessages` - Search email messages
- `sendMail` - Send emails

Check available tools:
```bash
curl http://localhost:8001/agents/calendar
```

## 🔄 How It Works

1. User sends natural language request to agent
2. Azure OpenAI LLM understands intent and selects tools
3. LLM calls tools via OpenAI function calling
4. Agent routes tool calls to MCP server via streamable HTTP
5. MCP server executes tools (e.g., Microsoft Graph API)
6. LLM generates final response based on tool results

##  API Endpoints

- `GET /` - Health check
- `GET /agents/calendar` - Agent info (includes MCP connection status and available tools)
- `POST /agents/calendar/invoke` - Invoke agent with natural language request

## 📊 Response Format

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
    },
    {
      "name": "sendMail",
      "arguments": [
        {"name": "to", "value": ["alice@company.com", "bob@company.com"]},
        {"name": "subject", "value": "Meeting Invitation: Q4 Planning"},
        {"name": "body", "value": "You're invited to discuss Q4 planning tomorrow at 2pm."}
      ]
    }
  ]
}
```

## 🔍 Monitoring

Check MCP connection and available tools:
```bash
curl http://localhost:8001/agents/calendar | jq
```

Response:
```json
{
  "name": "calendar",
  "description": "Azure OpenAI-powered calendar scheduling agent",
  "deployment": "gpt-4.1",
  "mcp_connected": true,
  "mcp_server_url": "https://your-mcp-server.com/mcp",
  "tools": [
    "mcp_CalendarTools_graph_createEvent",
    "mcp_CalendarTools_graph_listEvents",
    "sendMail",
    "searchMessages"
  ]
}
```

## 🤖 Evaluating Your Own Agent

To integrate your own agent with the evaluation platform, implement a POST endpoint that accepts the request format shown above (in **📞 Invoke the Agent**) and returns the response format shown in **📊 Response Format**.

### Key Requirements

1. **Endpoint**: Any POST endpoint path of your choice (this example uses `/agents/calendar/invoke`)
2. **Authentication**: Must be unauthenticated (no API keys or tokens required)
3. **Request/Response**: Follow the `InvokeRequest` and `InvokeResponse` formats documented above in this README (see **📞 Invoke the Agent** for request structure and **📊 Response Format** for response structure), or reference the models in `agent_server.py`
4. **Tool Tracking**: Record all tool invocations with exact arguments for evaluation

See `agent_server.py` for a complete reference implementation.
