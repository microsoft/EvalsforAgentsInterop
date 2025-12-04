#!/usr/bin/env pwsh

# Evals for Agent Interop Infrastructure Deployment Script
# This script deploys the Bicep template to create Cosmos DB and Azure OpenAI resources

# Parameters
param(
    [Parameter(Mandatory=$false)]
    [Alias("g")]
    [string]$ResourceGroup,

    [Parameter(Mandatory=$false)]
    [Alias("l")]
    [string]$Location,

    [Parameter(Mandatory=$false)]
    [Alias("e")]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$false)]
    [Alias("n")]
    [string]$DeploymentName,

    [Parameter(Mandatory=$false)]
    [Alias("s")]
    [string]$UniqueSuffix,

    [Parameter(Mandatory=$false)]
    [Alias("h")]
    [switch]$Help
)

# Enable strict error handling
$ErrorActionPreference = "Stop"

# Set default values if not provided
if ([string]::IsNullOrEmpty($ResourceGroup)) {
    $ResourceGroup = "evals-interop-dev-rg"
}

if ([string]::IsNullOrEmpty($Location)) {
    $Location = "eastus"
}

if ([string]::IsNullOrEmpty($Environment)) {
    $Environment = "dev"
}

# Function to display usage
function Show-Usage {
    Write-Host "Usage: .\deploy.ps1 [OPTIONS]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor White
    Write-Host "  -ResourceGroup <name>    Resource group name (default: evals-interop-dev-rg)" -ForegroundColor Gray
    Write-Host "  -g <name>                Alias for -ResourceGroup" -ForegroundColor Gray
    Write-Host "  -Location <location>     Azure location (default: eastus)" -ForegroundColor Gray
    Write-Host "  -l <location>            Alias for -Location" -ForegroundColor Gray
    Write-Host "  -Environment <env>       Environment (dev|staging|prod) (default: dev)" -ForegroundColor Gray
    Write-Host "  -e <env>                 Alias for -Environment" -ForegroundColor Gray
    Write-Host "  -DeploymentName <name>   Deployment name (default: auto-generated)" -ForegroundColor Gray
    Write-Host "  -n <name>                Alias for -DeploymentName" -ForegroundColor Gray
    Write-Host "  -UniqueSuffix <suffix>   Unique suffix for resource names (default: auto-generated)" -ForegroundColor Gray
    Write-Host "  -s <suffix>              Alias for -UniqueSuffix" -ForegroundColor Gray
    Write-Host "  -Help                    Show this help message" -ForegroundColor Gray
    Write-Host "  -h                       Alias for -Help" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\deploy.ps1" -ForegroundColor Cyan
    Write-Host "  .\deploy.ps1 -ResourceGroup my-rg -Location westus2 -Environment prod" -ForegroundColor Cyan
    Write-Host "  .\deploy.ps1 -g my-rg -l westus2 -e prod" -ForegroundColor Cyan
    Write-Host ""
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Generate deployment name if not provided
if ([string]::IsNullOrEmpty($DeploymentName)) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $DeploymentName = "evals-interop-infra-$timestamp"
}

# Generate unique suffix for resource naming if not provided
if ([string]::IsNullOrEmpty($UniqueSuffix)) {
    try {
        $UniqueSuffix = -join ((97..122) + (48..57) | Get-Random -Count 6 | ForEach-Object {[char]$_})
    } catch {
        $UniqueSuffix = Get-Date -Format "HHmmss"
    }
}

Write-Host "🚀 Starting Evals for Agent Interop infrastructure deployment..." -ForegroundColor Cyan
Write-Host "📍 Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "🌍 Location: $Location" -ForegroundColor White
Write-Host "🏷️ Environment: $Environment" -ForegroundColor White
Write-Host "📦 Deployment Name: $DeploymentName" -ForegroundColor White
Write-Host ""

# Check if Azure CLI is installed
Write-Host "🔍 Checking Azure CLI..." -ForegroundColor Cyan
$azCommand = Get-Command az -ErrorAction SilentlyContinue
if (-not $azCommand) {
    Write-Host "❌ Azure CLI is not installed. Please install it first." -ForegroundColor Red
    Write-Host "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor DarkGray
    exit 1
}

# Check if user is logged in
try {
    $null = az account show 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Not logged in to Azure. Please run 'az login' first." -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "❌ Not logged in to Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Azure CLI is ready" -ForegroundColor Green

# Create resource group if it doesn't exist
Write-Host "🏗️ Creating resource group if it doesn't exist..." -ForegroundColor Cyan
az group create `
    --name $ResourceGroup `
    --location $Location `
    --output table
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create resource group" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Resource group ready" -ForegroundColor Green

# Deploy the Bicep template
Write-Host "🚀 Deploying infrastructure..." -ForegroundColor Cyan

# Get the script directory to find main.bicep
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bicepPath = Join-Path $scriptDir "main.bicep"

$deploymentOutput = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file $bicepPath `
    --parameters "environment=$Environment" "location=$Location" "uniqueSuffix=$UniqueSuffix" `
    --name $DeploymentName `
    --output json

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Extract outputs from deployment
    Write-Host "📋 Extracting configuration values..." -ForegroundColor Cyan
    
    try {
        $deploymentJson = $deploymentOutput | ConvertFrom-Json
        $outputs = $deploymentJson.properties.outputs
        
        $cosmosEndpoint = $outputs.cosmosEndpoint.value
        $cosmosKey = $outputs.cosmosKey.value
        $openAiEndpoint = $outputs.openAiEndpoint.value
        $openAiKey = $outputs.aiFoundryKey.value
        
        Write-Host "🎉 Infrastructure deployment completed!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Configuration Values for Your .env Files:" -ForegroundColor Cyan
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "🗄️  COSMOS DB:" -ForegroundColor Yellow
        Write-Host "   COSMOS_ENDPOINT=$cosmosEndpoint" -ForegroundColor White
        Write-Host "   COSMOS_KEY=$cosmosKey" -ForegroundColor White
        Write-Host "   COSMOS_DATABASE_NAME=interopevals" -ForegroundColor White
        Write-Host "   COSMOS_DATASETS_CONTAINER_NAME=datasets" -ForegroundColor White
        Write-Host "   COSMOS_TESTCASES_CONTAINER_NAME=testcases" -ForegroundColor White
        Write-Host "   COSMOS_AGENTS_CONTAINER_NAME=agents" -ForegroundColor White
        Write-Host ""
        Write-Host "🤖 AZURE OPENAI:" -ForegroundColor Yellow
        Write-Host "   AZURE_OPENAI_ENDPOINT=$openAiEndpoint" -ForegroundColor White
        Write-Host "   AZURE_OPENAI_API_KEY=$openAiKey" -ForegroundColor White
        Write-Host "   AZURE_OPENAI_DEPLOYMENT=gpt-4.1 # Make sure to manually deploy the model in the Azure Foundry Portal" -ForegroundColor White
        Write-Host "   AZURE_OPENAI_API_VERSION=2024-12-01-preview" -ForegroundColor White
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "🚀 Next steps:" -ForegroundColor Cyan
        Write-Host "   1. Manually deploy the GPT-4.1 model in the Azure AI Foundry portal" -ForegroundColor White
        Write-Host "   2. Copy the values above to your .env file at the root of the repo" -ForegroundColor White
        Write-Host "   3. Reference the README.md (../README.md) for instructions on running the local development environment" -ForegroundColor
        Write-Host ""
    }
    catch {
        Write-Host "❌ Failed to parse deployment output" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}
