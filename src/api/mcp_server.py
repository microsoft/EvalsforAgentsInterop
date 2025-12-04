"""Shared MCP server lifecycle management."""

from __future__ import annotations

from threading import Lock
from typing import Final

from fastmcp import FastMCP

from .mcp_service import load_and_register_tools

_SERVER_NAME: Final[str] = "Evals for Agent Interop MCP Server"
_server_lock = Lock()
_mcp_server: FastMCP | None = None


def get_mcp_server() -> FastMCP:
    """Return the singleton FastMCP server configured with all tools."""
    global _mcp_server
    if _mcp_server is None:
        with _server_lock:
            if _mcp_server is None:
                server = FastMCP(_SERVER_NAME)
                load_and_register_tools(server)
                _mcp_server = server
    return _mcp_server
