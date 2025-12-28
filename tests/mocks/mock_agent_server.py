"""
Mock Agent Server for Integration Testing

A lightweight mock agent that returns predictable responses for testing
the evaluation pipeline without requiring Azure OpenAI.
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json


class InvokeRequest(BaseModel):
    """Request to invoke the mock agent."""
    dataset_id: Optional[str] = None
    test_case_id: Optional[str] = None
    user_prompt: str


class InvokeResponse(BaseModel):
    """Response from the mock agent."""
    response: str
    tool_calls: List[Dict[str, Any]] = []


# Create the mock agent app
mock_agent_app = FastAPI(title="Mock Agent Server", version="1.0.0")


# Predefined responses for different test scenarios
MOCK_RESPONSES = {
    "success": {
        "response": "I have completed the task successfully.",
        "tool_calls": [
            {
                "name": "sendMail",
                "arguments": {
                    "to": ["client@example.com"],
                    "subject": "RE: Project Update",
                    "body": "Thank you for your message. I have addressed your concerns."
                },
                "response": {"status": "sent", "messageId": "msg_123"}
            }
        ]
    },
    "no_tools": {
        "response": "I don't have access to the required tools.",
        "tool_calls": []
    },
    "wrong_tool": {
        "response": "I sent a Teams message instead.",
        "tool_calls": [
            {
                "name": "sendTeamsMessage",
                "arguments": {"channel": "general", "message": "Hello"},
                "response": {"status": "sent"}
            }
        ]
    },
    "error": {
        "response": "An error occurred while processing your request.",
        "tool_calls": []
    }
}


@mock_agent_app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent": "mock",
        "version": "1.0.0"
    }


@mock_agent_app.get("/agents/mock")
async def agent_info():
    """Get information about the mock agent."""
    return {
        "name": "mock",
        "description": "Mock agent for testing",
        "deployment": "mock-deployment"
    }


@mock_agent_app.post("/agents/mock/invoke", response_model=InvokeResponse)
async def invoke_mock_agent(request: InvokeRequest, http_request: Request):
    """Invoke the mock agent with a user request.
    
    The mock agent returns different responses based on keywords in the prompt:
    - "success" or default: Returns a successful email send
    - "no_tools": Returns response with no tool calls
    - "wrong_tool": Returns response with wrong tool called
    - "error": Simulates an error response
    - "timeout": Raises an HTTPException to simulate timeout
    - "rate_limit": Raises 429 to simulate rate limiting
    """
    prompt_lower = request.user_prompt.lower()
    
    # Check for special test scenarios
    if "timeout" in prompt_lower:
        raise HTTPException(status_code=504, detail="Gateway Timeout")
    
    if "rate_limit" in prompt_lower or "429" in prompt_lower:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if "server_error" in prompt_lower or "500" in prompt_lower:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    if "no_tools" in prompt_lower:
        return InvokeResponse(**MOCK_RESPONSES["no_tools"])
    
    if "wrong_tool" in prompt_lower:
        return InvokeResponse(**MOCK_RESPONSES["wrong_tool"])
    
    if "error" in prompt_lower:
        return InvokeResponse(**MOCK_RESPONSES["error"])
    
    # Default: success scenario
    return InvokeResponse(**MOCK_RESPONSES["success"])


@mock_agent_app.post("/agents/calendar/invoke", response_model=InvokeResponse)
async def invoke_calendar_agent(request: InvokeRequest, http_request: Request):
    """Legacy calendar endpoint - redirects to mock agent."""
    return await invoke_mock_agent(request, http_request)


@mock_agent_app.post("/agents/email/invoke", response_model=InvokeResponse)
async def invoke_email_agent(request: InvokeRequest, http_request: Request):
    """Email agent endpoint - returns email-specific mock response."""
    return InvokeResponse(
        response="I have sent the email as requested.",
        tool_calls=[
            {
                "name": "sendMail",
                "arguments": {
                    "to": ["recipient@example.com"],
                    "cc": ["priya.desai@treyresearch.net"],
                    "bcc": [],
                    "subject": "RE: Client Request",
                    "body": "Dear Client,\n\nThank you for reaching out.\n\nBest regards,\nJordan Evans"
                },
                "response": {"status": "sent", "messageId": "msg_456"}
            }
        ]
    )


@mock_agent_app.post("/agents/meeting/invoke", response_model=InvokeResponse)
async def invoke_meeting_agent(request: InvokeRequest, http_request: Request):
    """Meeting agent endpoint - returns meeting-specific mock response."""
    return InvokeResponse(
        response="I have scheduled the meeting and sent confirmations.",
        tool_calls=[
            {
                "name": "searchMessages",
                "arguments": {"queryString": "from:client@example.com subject:meeting"},
                "response": {"messages": [{"id": "msg_1", "subject": "Meeting Request"}]}
            },
            {
                "name": "listEvents",
                "arguments": {"userId": "organizer@fabrikam.com"},
                "response": {"events": []}
            },
            {
                "name": "createEvent",
                "arguments": {
                    "subject": "Project Discussion",
                    "attendees": ["client@example.com", "organizer@fabrikam.com"]
                },
                "response": {"eventId": "evt_123", "status": "created"}
            },
            {
                "name": "sendMail",
                "arguments": {
                    "to": ["client@example.com"],
                    "subject": "Meeting Confirmed: Project Discussion"
                },
                "response": {"status": "sent"}
            }
        ]
    )


# Export for use in integration tests
def get_mock_agent_app():
    """Get the mock agent FastAPI app for testing."""
    return mock_agent_app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mock_agent_app, host="0.0.0.0", port=8002)
