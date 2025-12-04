#!/bin/bash

# Evals for Agent Interop Infrastructure Deployment Script
# This script deploys the Bicep template to create Cosmos DB and Azure OpenAI resources

set -e

# Default values
RESOURCE_GROUP_NAME="evals-interop-dev-rg"
LOCATION="eastus"
DEPLOYMENT_NAME="evals-interop-infra-$(date +%Y%m%d-%H%M%S)"
ENVIRONMENT="dev"
UNIQUE_SUFFIX=""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -g, --resource-group    Resource group name (default: $RESOURCE_GROUP_NAME)"
    echo "  -l, --location          Azure location (default: $LOCATION)"
    echo "  -e, --environment       Environment (dev|staging|prod) (default: $ENVIRONMENT)"
    echo "  -n, --deployment-name   Deployment name (default: auto-generated)"
    echo "  -s, --unique-suffix     Unique suffix for resource names (default: auto-generated)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 -g my-rg -l westus2 -e prod"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP_NAME="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--deployment-name)
            DEPLOYMENT_NAME="$2"
            shift 2
            ;;
        -s|--unique-suffix)
            UNIQUE_SUFFIX="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "🚀 Starting Evals for Agent Interop infrastructure deployment..."
echo "📍 Resource Group: $RESOURCE_GROUP_NAME"
echo "🌍 Location: $LOCATION"
echo "🏷️ Environment: $ENVIRONMENT"
echo "📦 Deployment Name: $DEPLOYMENT_NAME"
echo ""

# Generate unique suffix if not provided
if [ -z "$UNIQUE_SUFFIX" ]; then
    UNIQUE_SUFFIX=$(tr -dc 'a-z0-9' </dev/urandom | head -c 6 || echo "$(date +%H%M%S)")
fi

# Check if Azure CLI is installed and user is logged in
echo "🔍 Checking Azure CLI..."
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI is ready"

# Create resource group if it doesn't exist
echo "🏗️ Creating resource group if it doesn't exist..."
az group create \
    --name "$RESOURCE_GROUP_NAME" \
    --location "$LOCATION" \
    --output table

echo "✅ Resource group ready"

# Deploy the Bicep template
echo "🚀 Deploying infrastructure..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file "main.bicep" \
    --parameters "environment=$ENVIRONMENT" "location=$LOCATION" "uniqueSuffix=$UNIQUE_SUFFIX" \
    --name "$DEPLOYMENT_NAME" \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ Deployment completed successfully!"
    echo ""
    
    # Extract outputs from deployment using Azure CLI query
    echo "📋 Extracting configuration values..."
    COSMOS_ENDPOINT=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$DEPLOYMENT_NAME" \
        --query 'properties.outputs.cosmosEndpoint.value' \
        --output tsv)
    COSMOS_KEY=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$DEPLOYMENT_NAME" \
        --query 'properties.outputs.cosmosKey.value' \
        --output tsv)
    OPENAI_ENDPOINT=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$DEPLOYMENT_NAME" \
        --query 'properties.outputs.openAiEndpoint.value' \
        --output tsv)
    OPENAI_KEY=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$DEPLOYMENT_NAME" \
        --query 'properties.outputs.aiFoundryKey.value' \
        --output tsv)
    
    echo "🎉 Infrastructure deployment completed!"
    echo ""
    echo "📋 Configuration Values for Your .env Files:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🗄️  COSMOS DB:"
    echo "   COSMOS_ENDPOINT=$COSMOS_ENDPOINT"
    echo "   COSMOS_KEY=$COSMOS_KEY"
    echo "   COSMOS_DATABASE_NAME=interopevals"
    echo "   COSMOS_DATASETS_CONTAINER_NAME=datasets"
    echo "   COSMOS_TESTCASES_CONTAINER_NAME=testcases"
    echo "   COSMOS_AGENTS_CONTAINER_NAME=agents"
    echo ""
    echo "🤖 AZURE OPENAI:"
    echo "   AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT"
    echo "   AZURE_OPENAI_API_KEY=$OPENAI_KEY"
    echo "   AZURE_OPENAI_DEPLOYMENT=gpt-4.1 # Make sure to manually deploy the model in the Azure Foundry Portal"
    echo "   AZURE_OPENAI_API_VERSION=2024-12-01-preview"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Manually deploy the GPT-4.1 model in the Azure AI Foundry portal"
    echo "   2. Copy the values above to your .env file at the root of the repo"
    echo "   3. Reference the README.md (../README.md) for instructions on running the local development environment"
    echo ""
else
    echo "❌ Deployment failed!"
    exit 1
fi