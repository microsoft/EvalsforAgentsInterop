// Main Bicep template for Evals for Agent Interop local development infrastructure
// Creates only Cosmos DB and Azure OpenAI resources

targetScope = 'resourceGroup'

// Parameters
@description('Environment suffix (e.g., dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Unique suffix to ensure globally unique resource names')
param uniqueSuffix string = uniqueString(resourceGroup().id)

// Variables
var resourcePrefix = 'evals-interop-${environment}'
var cosmosAccountName = '${resourcePrefix}-cosmos-${uniqueSuffix}'
var openAiAccountName = '${resourcePrefix}-openai-${uniqueSuffix}'

// Cosmos DB Account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxIntervalInSeconds: 300
      maxStalenessPrefix: 100000
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
  }
}

// Cosmos DB Database
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: 'interopevals'
  properties: {
    resource: {
      id: 'interopevals'
    }
  }
}

// Cosmos DB Containers
resource datasetsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'datasets'
  properties: {
    resource: {
      id: 'datasets'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource testcasesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'testcases'
  properties: {
    resource: {
      id: 'testcases'
      partitionKey: {
        paths: ['/dataset_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource agentsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'agents'
  properties: {
    resource: {
      id: 'agents'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource evaluationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'evaluations'
  properties: {
    resource: {
      id: 'evaluations'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

// Azure AI Foundry Account (similar to evalsharedfoundry.cognitiveservices.azure.com)
resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: openAiAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiAccountName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
  }
}

// Outputs for local development configuration
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosKey string = cosmosAccount.listKeys().primaryMasterKey
output cosmosDatabaseName string = cosmosDatabase.name
output cosmosContainers object = {
  datasets: datasetsContainer.name
  testcases: testcasesContainer.name
  agents: agentsContainer.name
  evaluations: evaluationsContainer.name
}

output openAiEndpoint string = 'https://${openAiAccountName}.openai.azure.com/'
output aiFoundryKey string = aiFoundryAccount.listKeys().key1
output aiFoundryApiVersion string = '2024-12-01-preview'

// Environment file template output
output envFileTemplate string = '''
# Cosmos DB
COSMOS_ENDPOINT=${cosmosAccount.properties.documentEndpoint}
COSMOS_KEY=${cosmosAccount.listKeys().primaryMasterKey}
COSMOS_DATABASE_NAME=${cosmosDatabase.name}
COSMOS_DATASETS_CONTAINER_NAME=${datasetsContainer.name}
COSMOS_TESTCASES_CONTAINER_NAME=${testcasesContainer.name}
COSMOS_AGENTS_CONTAINER_NAME=${agentsContainer.name}

# Azure AI Foundry
AZURE_OPENAI_ENDPOINT=https://${openAiAccountName}.openai.azure.com/
AZURE_OPENAI_API_KEY=${aiFoundryAccount.listKeys().key1}
AZURE_OPENAI_DEPLOYMENT=gpt-4.1  # Fill this in after adding your model in the Foundry portal
AZURE_OPENAI_API_VERSION=2024-12-01-preview  # Update as needed for your model
'''