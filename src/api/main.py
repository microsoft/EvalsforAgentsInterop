from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .controllers import router
from . import config
from .mcp_middleware import MCP400ErrorHandlerMiddleware
from .mcp_server import get_mcp_server

mcp = get_mcp_server()
mcp_app = mcp.http_app(path="/")

app = FastAPI(title=config.API_TITLE, docs_url="/api/docs", lifespan=mcp_app.lifespan)

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