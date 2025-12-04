import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Cosmos DB
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE_NAME", "interopevals")
COSMOS_DATASETS_CONTAINER = os.getenv("COSMOS_DATASETS_CONTAINER_NAME", "datasets")
COSMOS_TESTCASES_CONTAINER = os.getenv("COSMOS_TESTCASES_CONTAINER_NAME", "testcases")
COSMOS_AGENTS_CONTAINER = os.getenv("COSMOS_AGENTS_CONTAINER_NAME", "agents")
COSMOS_EVALUATIONS_CONTAINER = os.getenv("COSMOS_EVALUATIONS_CONTAINER_NAME", "evaluations")

# API
API_TITLE = os.getenv("API_TITLE", "Evals for Agent Interop API")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# Azure OpenAI (uses DefaultAzureCredential if API key not provided)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")  # Optional, for Docker/CI
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Evaluation Configuration  
MAX_CONCURRENT_TESTS = int(os.getenv("MAX_CONCURRENT_TESTS", "5"))
EVALUATION_TIMEOUT_SECONDS = int(os.getenv("EVALUATION_TIMEOUT_SECONDS", "300"))