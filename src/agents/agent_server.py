"""
Standalone Azure OpenAI Calendar Agent

A minimal FastAPI server providing an LLM-powered calendar scheduling agent.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import uvicorn
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class InvokeRequest(BaseModel):
    """Request model for agent invocation."""
    dataset_id: str
    test_case_id: str
    agent_id: str
    evaluation_run_id: str
    input: str


class ToolArgument(BaseModel):
    """Tool argument with name and value."""
    name: str
    value: Any


class ToolCall(BaseModel):
    """Tool call record."""
    name: str
    arguments: List[ToolArgument]
    response: Optional[Dict[str, Any]] = None  # MCP tool response


class InvokeResponse(BaseModel):
    """Response from agent invocation."""
    response: str
    tool_calls: List[ToolCall]


# ============================================================================
# Calendar Agent
# ============================================================================

class CalendarAgent:
    """Azure OpenAI-powered calendar scheduling agent."""
    
    def __init__(self, mcp_server_url: Optional[str] = None):
        # Initialize Azure OpenAI client
        # Prefer API key (for Docker), fallback to Entra ID (for local dev)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://oai-exp.openai.azure.com/")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        
        if api_key:
            logger.info("Using API key authentication for Azure OpenAI")
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version
            )
        else:
            logger.info("Using Entra ID (DefaultAzureCredential) authentication for Azure OpenAI")
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default"
            )
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=api_version
            )
        
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
        
        # MCP server configuration
        self.mcp_server_url = mcp_server_url or os.getenv("MCP_SERVER_URL")
        self.mcp_session: Optional[ClientSession] = None
        self.mcp_connected = False
        self._mcp_read = None
        self._mcp_write = None
        self._mcp_context = None
        self._get_session_id = None
        
        # Tools will be populated from MCP server
        self.tools = []
        
        # Correlation headers for MCP tool calls
        self.correlation_headers: Dict[str, str] = {}
    
    async def connect_mcp(self):
        """Connect to MCP server over HTTP with streamable transport and keep connection alive."""
        await self.connect_mcp_with_headers()
    
    async def connect_mcp_with_headers(self, headers: Optional[Dict[str, str]] = None):
        """Connect to MCP server with optional correlation headers."""
        if not self.mcp_server_url:
            logger.warning("No MCP server URL configured - agent will not have any tools available")
            logger.warning("Set MCP_SERVER_URL environment variable or pass mcp_server_url parameter")
            return
        
        try:
            logger.info(f"Attempting to connect to MCP server at {self.mcp_server_url}")
            
            # Use streamable HTTP client (newer transport, replaces deprecated SSE)
            logger.info(f"Connecting with streamable HTTP transport to: {self.mcp_server_url}")
            
            # Pass correlation headers to MCP server
            mcp_headers = headers or {}
            if self.correlation_headers:
                mcp_headers.update(self.correlation_headers)
                logger.info(f"Using correlation headers for MCP connection: {list(mcp_headers.keys())}")
            
            # Create streamable HTTP client connection
            # Returns: (read_stream, write_stream, get_session_id_callback)
            self._mcp_context = streamablehttp_client(self.mcp_server_url, headers=mcp_headers)
            read, write, get_session_id = await self._mcp_context.__aenter__()
            self._mcp_read = read
            self._mcp_write = write
            self._get_session_id = get_session_id
            
            logger.info(f"MCP HTTP connection established, session ID callback available")
            
            logger.info("MCP HTTP connection established, creating session...")
            
            # Create session - keep it alive by not using context manager
            self.mcp_session = ClientSession(read, write)
            await self.mcp_session.__aenter__()
            
            logger.info("MCP client session created, initializing...")
            await self.mcp_session.initialize()
            logger.info("MCP session initialized successfully")
            
            self.mcp_connected = True
            
            # List available tools from MCP server
            logger.info("Requesting tool list from MCP server...")
            tools_result = await self.mcp_session.list_tools()
            logger.info(f"Connected to MCP server with {len(tools_result.tools)} tools: {[t.name for t in tools_result.tools]}")
            
            # Update tool definitions from MCP server
            self._update_tools_from_mcp(tools_result.tools)
            logger.info(f"Tool definitions updated from MCP server")
                    
        except ConnectionError as e:
            logger.error(f"Connection error to MCP server at {self.mcp_server_url}: {e}", exc_info=True)
            logger.error("Agent will not have any tools available")
            self.mcp_connected = False
        except TimeoutError as e:
            logger.error(f"Timeout connecting to MCP server at {self.mcp_server_url}: {e}", exc_info=True)
            logger.error("Agent will not have any tools available")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {type(e).__name__}: {e}", exc_info=True)
            logger.error("Agent will not have any tools available")
            self.mcp_connected = False
    
    async def disconnect_mcp(self):
        """Disconnect from MCP server and cleanup resources."""
        if self.mcp_session:
            try:
                await self.mcp_session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP session: {e}")
        
        if self._mcp_context:
            try:
                await self._mcp_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP context: {e}")
        
        self.mcp_connected = False
        logger.info("Disconnected from MCP server")
    
    def _update_tools_from_mcp(self, mcp_tools):
        """Update OpenAI function definitions from MCP tool schemas."""
        # Convert MCP tool definitions to OpenAI function calling format
        self.tools = []
        for tool in mcp_tools:
            self.tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}}
                }
            })
    
    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """Process user request and return response with tool uses."""
        
        logger.info(f"Processing request for test case: {request.test_case_id}")
        
        # Initialize conversation with user message
        messages = [
            {
                "role": "system",
                "content": """You are a helpful calendar scheduling assistant with access to powerful tools for managing calendars, emails, and users.

IMPORTANT: You MUST use the available tools to complete user requests. Do NOT try to complete tasks manually or describe what you would do - actually use the tools. Please do not respond asking for more details, use default values if you need to fill in missing parameters for a tool call.

Available capabilities:
- Send emails using sendMail
- Search for messages using searchMessages
- Create, list, and manage calendar events
- Find and list users in the organization

When a user asks you to perform an action (like "send an email" or "schedule a meeting"), you should:
1. Use the appropriate tool to perform the action
2. Provide a detailed confirmation that includes ALL key details

For CALENDAR SCHEDULING with conflict checking:
- If there's a conflict at the requested time, you MUST choose a DIFFERENT time slot
- Do NOT schedule at a conflicting time - find the next available slot instead
- If asked to reschedule and notify someone, you MUST both reschedule AND send an email notification

After completing any action, your confirmation MUST:
- State what was done successfully
- List all recipients, dates, times, or other key information
- Summarize ALL the content/points that were included (e.g., for emails, list every topic mentioned)

Always prefer using tools over describing what should be done."""
            },
            {
                "role": "user",
                "content": request.input
            }
        ]
        
        tool_calls = []
        max_iterations = 10
        
        for iteration in range(max_iterations):
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # If no tool calls, we're done
            if not message.tool_calls:
                final_response = message.content or "Task completed."
                logger.info(f"🏁 Agent finished without tool calls. Response: {final_response[:100]}...")
                break
            
            # Add assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"🔧 TOOL CALL: {function_name}")
                logger.info(f"   Arguments: {json.dumps(function_args, indent=2)}")
                
                # Execute the tool
                result = await self._execute_tool(function_name, function_args)
                logger.info(f"✅ TOOL RESULT: {function_name} completed")
                
                # Record tool call with response
                tool_calls.append(ToolCall(
                    name=function_name,
                    arguments=[
                        ToolArgument(name=k, value=v)
                        for k, v in function_args.items()
                    ],
                    response=result  # Capture the MCP tool response
                ))
                
                # Add tool response to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
        else:
            # Max iterations reached
            final_response = "Task completed after maximum iterations."
            logger.warning(f"⚠️  Max iterations ({max_iterations}) reached")
        
        # Summary logging
        logger.info(f"📊 EXECUTION SUMMARY:")
        logger.info(f"   Total tool calls: {len(tool_calls)}")
        if tool_calls:
            for i, tc in enumerate(tool_calls, 1):
                logger.info(f"   {i}. {tc.name}")
        else:
            logger.warning(f"   ⚠️  NO TOOLS WERE CALLED!")
        
        return InvokeResponse(
            response=final_response,
            tool_calls=tool_calls
        )
    
    async def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function via MCP or fallback to mocks."""
        
        # Try MCP server first if connected
        if self.mcp_connected and self.mcp_session:
            try:
                logger.info(f"→ Executing MCP tool: {function_name}")
                result = await self.mcp_session.call_tool(function_name, arguments)
                logger.info(f"← MCP tool {function_name} responded successfully")
                
                # Parse MCP response
                if result.content:
                    content = result.content[0]
                    logger.info(f"MCP response content type: {type(content)}, hasattr text: {hasattr(content, 'text')}")
                    if hasattr(content, 'text'):
                        parsed = json.loads(content.text)
                        logger.info(f"Successfully parsed MCP response: {parsed}")
                        return parsed
                    else:
                        result_str = str(content)
                        logger.info(f"MCP content as string: {result_str}")
                        return {"result": result_str}
                logger.warning(f"MCP tool {function_name} returned no content")
                return {"status": "success"}
                
            except json.JSONDecodeError as e:
                logger.error(f"MCP tool {function_name} returned invalid JSON: {e}, content: {content.text if hasattr(content, 'text') else content}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"MCP tool call failed for {function_name}: {type(e).__name__}: {e}", exc_info=True)
                raise
        
        # No MCP connection - return error
        error_msg = f"Tool {function_name} not available - MCP server not connected"
        logger.error(error_msg)
        return {"error": error_msg, "mcp_connected": False}


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(title="Calendar Agent", version="1.0.0")

mcp_server_url = os.getenv("MCP_SERVER_URL")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent": "calendar",
        "version": "1.0.0"
    }


@app.post("/agents/calendar/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest, http_request: Request):
    """Invoke the calendar agent with a user request."""
    try:
        # Extract correlation headers
        correlation_headers = {}
        correlation_id = http_request.headers.get('x-correlationid')
        test_case_id = http_request.headers.get('x-testcaseid')
        
        if correlation_id:
            correlation_headers['x-correlationid'] = correlation_id
        if test_case_id:
            correlation_headers['x-testcaseid'] = test_case_id
            
        logger.info(f"Processing request with correlation headers: {correlation_headers}")
        
        # Create a fresh agent instance with its own MCP connection for this request
        request_agent = CalendarAgent(mcp_server_url)
        
        # Connect with correlation headers if we have any
        if correlation_headers:
            await request_agent.connect_mcp_with_headers(correlation_headers)
        else:
            await request_agent.connect_mcp()
        
        try:
            # Process the request with the dedicated agent instance
            response = await request_agent.invoke(request)
            return response
        finally:
            # Always cleanup the per-request agent
            await request_agent.disconnect_mcp()
            
    except Exception as e:
        logger.error(f"Error invoking agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/calendar")
async def agent_info():
    """Get information about the calendar agent."""
    return {
        "name": "calendar",
        "description": "Azure OpenAI-powered calendar scheduling agent",
        "deployment": deployment_name,
        "mcp_server_url": mcp_server_url,
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Calendar Agent server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
