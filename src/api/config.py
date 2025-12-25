"""
Configuration Module

Loads environment variables and provides configuration constants for the API.

==============================================================================
FEATURES CONFIGURED IN THIS MODULE:
==============================================================================

1. RETRY CONFIGURATION FOR RATE LIMITING (Feature: rate-limit-retry)
   - RETRY_MAX_ATTEMPTS: How many times to retry before giving up
   - RETRY_BASE_DELAY: Initial delay (seconds), doubles each retry
   - RETRY_MAX_DELAY: Maximum delay cap to prevent excessive waits

==============================================================================
"""

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

# ==============================================================================
# RETRY CONFIGURATION FOR RATE LIMITING (Feature: rate-limit-retry)
# ==============================================================================
# These settings control how the evaluator handles Azure OpenAI 429 errors.
# Adjust these values based on your Azure OpenAI tier and quota:
#
# - RETRY_MAX_ATTEMPTS: More attempts = more resilient, but longer potential wait
# - RETRY_BASE_DELAY: Higher = more conservative, lower = more aggressive
# - RETRY_MAX_DELAY: Cap to prevent waiting forever on persistent rate limits
#
# With defaults (5 attempts, 2s base): waits 2s, 4s, 8s, 16s, 32s = 62s max
# ==============================================================================
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "5"))  # Max retry attempts for rate limits
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))  # Base delay in seconds
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "60.0"))   # Max delay between retries