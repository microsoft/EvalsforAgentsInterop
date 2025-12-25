"""
Main FastAPI Application Entry Point

==============================================================================
FEATURES IMPLEMENTED IN THIS MODULE:
==============================================================================

1. ORPHAN EVALUATION CLEANUP ON STARTUP (Feature: orphan-cleanup)
   - cleanup_orphaned_evaluations() called during lifespan startup
   - Automatically cancels evaluations that were "running" when server crashed
   - Prevents accumulation of stuck evaluations that confuse users

==============================================================================
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from .controllers import router
from . import config
from .mcp_middleware import MCP400ErrorHandlerMiddleware
from .mcp_server import get_mcp_server
from .cosmos_service import get_cosmos_service
from .evaluator_service import get_evaluator_service

logger = logging.getLogger(__name__)

mcp = get_mcp_server()
mcp_app = mcp.http_app(path="/")


# ==============================================================================
# LIFESPAN MANAGER (Feature: orphan-cleanup)
# ==============================================================================
# This async context manager handles server startup and shutdown.
# On startup, it cleans up any evaluations that were left in "running" state
# from a previous server crash or restart. This is important because:
# - Users expect "running" evaluations to be actively processing
# - Orphaned evaluations would never complete on their own
# - Cleaning them up on restart prevents confusion
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Combined lifespan manager for MCP and evaluation cleanup.
    
    Startup actions:
    1. Initialize database and evaluator services
    2. Cancel any orphaned evaluations from previous runs
    3. Hand off to MCP's lifespan manager
    
    Shutdown actions:
    1. Log shutdown message
    """
    # Startup: Clean up orphaned evaluations (Feature: orphan-cleanup)
    logger.info("Starting API server...")
    try:
        db = get_cosmos_service()
        evaluator = get_evaluator_service(db)
        # This marks any 'running' or 'pending' evaluations as 'cancelled'
        await evaluator.cleanup_orphaned_evaluations()
        logger.info("Orphaned evaluation cleanup completed")
    except Exception as e:
        logger.error(f"Error during startup cleanup: {str(e)}")
    
    # Delegate to MCP lifespan for its startup/shutdown
    async with mcp_app.lifespan(app):
        yield
    
    # Shutdown
    logger.info("API server shutting down...")


app = FastAPI(title=config.API_TITLE, docs_url="/api/docs", lifespan=lifespan)

app.mount("/mcp", mcp_app)

# Add MCP 400 error handling middleware
app.add_middleware(MCP400ErrorHandlerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Evals for Agent Interop API", "docs": "/api/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host=config.API_HOST, port=config.API_PORT, reload=True)