"""Middleware for handling MCP server errors gracefully."""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

class MCP400ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle 400 errors specifically for MCP endpoints."""
    
    async def dispatch(self, request: Request, call_next):
        """Handle 400 Bad Request errors gracefully"""
        try:
            # Log incoming request for debugging
            if request.url.path.startswith("/mcp"):
                logger.info(f"MCP request to {request.url.path}")
                
                # Try to read and validate request body for MCP endpoints
                if request.method == "POST":
                    try:
                        body = await request.body()
                        if body:
                            # Try to parse JSON to catch malformed requests early
                            json.loads(body.decode('utf-8'))
                            # Reset the body for the next middleware
                            request._body = body
                    except json.JSONDecodeError as je:
                        logger.warning(f"Invalid JSON in MCP request: {je}")
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "Bad Request",
                                "message": "Invalid JSON format in request body",
                                "path": str(request.url.path)
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Error reading request body: {e}")
            
            response = await call_next(request)
            
            # If this is a 400 error on an MCP endpoint, handle it gracefully
            if (response.status_code == 400 and 
                request.url.path.startswith("/mcp")):
                logger.warning(f"Intercepted 400 error for MCP endpoint: {request.url.path}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": "Invalid MCP request format",
                        "path": str(request.url.path)
                    }
                )
            
            return response
            
        except HTTPException as e:
            # Handle HTTPException with 400 status code for MCP paths only
            if (e.status_code == 400 and 
                request.url.path.startswith("/mcp")):
                logger.warning(f"Handled 400 HTTPException for MCP endpoint: {request.url.path} - {e.detail}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": str(e.detail),
                        "path": str(request.url.path)
                    }
                )
            # Re-raise other HTTP exceptions
            raise
            
        except json.JSONDecodeError as je:
            # Handle JSON decode errors specifically for MCP paths
            if request.url.path.startswith("/mcp"):
                logger.error(f"JSON decode error in MCP endpoint {request.url.path}: {je}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": "Invalid JSON in request body",
                        "path": str(request.url.path)
                    }
                )
            raise
            
        except Exception as e:
            # Only handle exceptions for MCP paths that might result in 400 errors
            if request.url.path.startswith("/mcp"):
                logger.error(f"Error in MCP endpoint {request.url.path}: {type(e).__name__}: {e}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": "MCP request processing failed",
                        "type": type(e).__name__,
                        "details": str(e),
                        "path": str(request.url.path)
                    }
                )
            # Re-raise exceptions for non-MCP paths
            raise