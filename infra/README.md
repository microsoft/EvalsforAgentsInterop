# Evals for Agent Interop Infrastructure

This directory contains Infrastructure as Code (IaC) templates for deploying Azure resources needed for local development of Evals for Agent Interop.

## 📋 Resources Created

The Bicep template creates the following Azure resources:

### 🗄️ Azure Cosmos DB
- **Account**: Serverless NoSQL database
- **Database**: `interopevals`
- **Containers**:
  - `datasets` (partitioned by `/id`)
  - `testcases` (partitioned by `/dataset_id`)
  - `agents` (partitioned by `/id`)
  - `evaluations` (partitioned by `/id`)

### 🤖 Azure OpenAI
- **Account**: Azure Foundry resource.
     - You will need to manually deploy GPT 4.1 from the Azure Foundry portal.

## 🚀 Quick Start

### Prerequisites

1. **Azure CLI**: [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Azure Subscription**: Active Azure subscription
3. **Permissions**: Contributor role on the subscription or resource group

### Login to Azure

```bash
az login
```

### Deploy Infrastructure

Choose your preferred deployment method:

#### Option 1: PowerShell (Recommended for Windows)
```powershell
cd infra
.\deploy.ps1
```

#### Option 2: Bash Script
```bash
cd infra
chmod +x deploy.sh
./deploy.sh
```

#### Option 3: Manual Azure CLI
```bash
cd infra

# Create resource group
az group create --name evals-interop-dev-rg --location eastus

# Deploy template with parameters file
az deployment group create \
  --resource-group evals-interop-dev-rg \
  --template-file main.bicep \
  --parameters main.parameters.json

# Or deploy with inline parameters
az deployment group create \
  --resource-group evals-interop-dev-rg \
  --template-file main.bicep \
  --parameters environment=dev
```

## 🎛️ Deployment Options

### Script Parameters

Both `deploy.sh` and `deploy.ps1` accept the following command-line parameters:

| Parameter | Alias | Default | Description |
|-----------|-------|---------|-------------|
| `--resource-group` / `-ResourceGroup` | `-g` | `evals-interop-dev-rg` | Name of the Azure resource group |
| `--location` / `-Location` | `-l` | `eastus` | Azure region for deployment |
| `--environment` / `-Environment` | `-e` | `dev` | Environment suffix (dev/staging/prod) |
| `--deployment-name` / `-DeploymentName` | `-n` | auto-generated | Custom deployment name |
| `--unique-suffix` / `-UniqueSuffix` | `-s` | auto-generated | Unique suffix for resource names |
| `--help` / `-Help` | `-h` | N/A | Display help message |

**Examples:**
```bash
# Bash - Deploy with custom resource group
./deploy.sh -g my-custom-rg

# Bash - Deploy to production in West Europe
./deploy.sh -g my-prod-rg -l westeurope -e prod

# PowerShell - Deploy with custom resource group
.\deploy.ps1 -g my-custom-rg

# PowerShell - Deploy to production in West Europe  
.\deploy.ps1 -ResourceGroup my-prod-rg -Location westeurope -Environment prod
```

### Bicep Template Parameters

All parameters have defaults and are optional:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `environment` | `dev` | Environment suffix (dev/staging/prod) |
| `location` | resource group location | Azure region |
| `uniqueSuffix` | auto-generated from RG | Unique suffix for resource names |

You can deploy without any parameters or override specific values as needed.

### Custom Deployment

```bash
# Deploy to production environment in West Europe
./deploy.sh -g evals-interop-prod-rg -l westeurope -e prod

# PowerShell equivalent
.\deploy.ps1 -ResourceGroupName "evals-interop-prod-rg" -Location "westeurope" -Environment "prod"
```

## 📝 Environment File

After successful deployment:

1. Manually deploy GPT 4.1 in the Azure Foundry portal
2. Copy the output values from the deployment script to your `.env` file at the root of the repository

The `.env` file contains all configuration for both API and Agent services, including connection strings and keys needed for local development.

## 🔧 Manual Configuration

If you prefer to configure manually, the deployment outputs the following values:

```bash
# Get deployment outputs
az deployment group show \
  --resource-group evals-interop-dev-rg \
  --name <deployment-name> \
  --query properties.outputs
```

## 💰 Cost Optimization

The template uses cost-effective configurations:

- **Cosmos DB**: Serverless billing (pay-per-use)
- **Azure OpenAI**: Standard pricing with minimal capacity

Estimated monthly cost for light development usage: **$10-50 USD**

## 🧹 Cleanup

To delete all resources:

```bash
# Delete the entire resource group
az group delete --name evals-interop-dev-rg --yes --no-wait
```

## 🔒 Security Notes

- **Keys in .env files**: These contain sensitive credentials. Never commit them to version control.
- **Network Access**: Resources are configured for public access to support local development.
- **Production**: Consider using managed identities and private endpoints for production deployments.

## 🛠️ Troubleshooting

### Common Issues

1. **"Deployment failed"**: Check Azure CLI version and login status
2. **"Resource name already exists"**: The template uses unique suffixes, but you can specify custom names
3. **"Insufficient permissions"**: Ensure you have Contributor role on the subscription

### Debug Commands

```bash
# Check Azure CLI login
az account show

# List deployments
az deployment group list --resource-group evals-interop-dev-rg

# Get deployment details
az deployment group show --resource-group evals-interop-dev-rg --name <deployment-name>
```

## 📚 Next Steps

After deployment:

1. Manually deploy GPT 4.1 in the Azure Foundry portal
2. Copy the output values from the deployment script to your `.env` file at the root of the repository
3. See [README.md](../README.md) for instructions on how to run services locally

## 📖 Additional Resources

- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Azure OpenAI Service Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure Bicep Documentation](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/)