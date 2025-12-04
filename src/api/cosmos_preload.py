#!/usr/bin/env python3
"""
Cosmos DB Preload Script

This script loads evaluation datasets from the data/eval folder and uploads them to Cosmos DB.
It separates the dataset metadata from test cases, storing them in separate containers as expected
by the API architecture.

Usage:
    python cosmos_preload.py [--dry-run] [--force] [--file filename.json]

Arguments:
    --dry-run: Show what would be uploaded without actually uploading
    --force: Overwrite existing datasets with the same ID
    --file: Process only a specific file instead of all files in the directory
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add the API module to Python path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

# Import from models
from models import EvaluatorContract

# Import the required modules by adding __init__.py behavior
import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env automatically from repo root
load_dotenv()

# Configure Cosmos settings directly
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE_NAME", "interopevals")
COSMOS_DATASETS_CONTAINER = os.getenv("COSMOS_DATASETS_CONTAINER_NAME", "datasets")
COSMOS_TESTCASES_CONTAINER = os.getenv("COSMOS_TESTCASES_CONTAINER_NAME", "testcases")


async def load_sample_file(file_path: Path) -> EvaluatorContract:
    """Load and validate a single JSON file as an EvaluatorContract"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate against schema
        contract = EvaluatorContract(**data)
        return contract
    except Exception as e:
        raise ValueError(f"Failed to load {file_path}: {e}")


def create_cosmos_service():
    """Create a simplified Cosmos service for the preload script."""
    
    class SimpleCosmosService:
        def __init__(self):
            credential = COSMOS_KEY if COSMOS_KEY else DefaultAzureCredential()
            self.client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
            self._database = None
            self._datasets_container = None
            self._testcases_container = None
        
        async def _ensure_initialized(self):
            """Initialize database and containers"""
            if self._datasets_container is None:
                import asyncio
                # Run blocking I/O in thread pool
                self._database = await asyncio.to_thread(
                    self.client.create_database_if_not_exists,
                    COSMOS_DATABASE
                )
                self._datasets_container = await asyncio.to_thread(
                    self._database.create_container_if_not_exists,
                    id=COSMOS_DATASETS_CONTAINER,
                    partition_key=PartitionKey(path="/id")
                )
                self._testcases_container = await asyncio.to_thread(
                    self._database.create_container_if_not_exists,
                    id=COSMOS_TESTCASES_CONTAINER,
                    partition_key=PartitionKey(path="/dataset_id")
                )
        
        async def create_dataset(self, contract: EvaluatorContract):
            """Create dataset and test cases from EvaluatorContract"""
            await self._ensure_initialized()
            import asyncio
            
            # Convert to dict for JSON serialization
            contract_dict = contract.model_dump(mode='json')
            
            # Create dataset document (without test_cases array)
            dataset_doc = {
                "id": contract_dict['id'],
                "metadata": contract_dict['metadata'],
                "seed": contract_dict['seed'],
                "test_case_ids": [],
                "created_at": contract_dict.get('created_at') or contract_dict['metadata']['created_at']
            }
            
            # Store dataset
            stored_dataset = await asyncio.to_thread(
                self._datasets_container.create_item,
                body=dataset_doc
            )
            
            # Store test cases separately and collect IDs
            test_case_ids = []
            for test_case in contract.test_cases:
                tc_dict = test_case.model_dump(mode='json')
                tc_dict['dataset_id'] = contract_dict['id']  # Ensure dataset_id is set
                
                stored_tc = await asyncio.to_thread(
                    self._testcases_container.create_item,
                    body=tc_dict
                )
                test_case_ids.append(stored_tc['id'])
            
            # Update dataset with test case IDs
            stored_dataset['test_case_ids'] = test_case_ids
            final_dataset = await asyncio.to_thread(
                self._datasets_container.replace_item,
                item=stored_dataset['id'],
                body=stored_dataset
            )
            
            return final_dataset
        
        async def get_dataset(self, dataset_id: str):
            """Get dataset by ID"""
            await self._ensure_initialized()
            import asyncio
            try:
                item = await asyncio.to_thread(
                    self._datasets_container.read_item,
                    item=dataset_id,
                    partition_key=dataset_id
                )
                return item
            except exceptions.CosmosResourceNotFoundError:
                return None
        
        async def delete_dataset(self, dataset_id: str):
            """Delete dataset and all its test cases"""
            await self._ensure_initialized()
            import asyncio
            try:
                # Delete all test cases first
                query = "SELECT * FROM c WHERE c.dataset_id = @dataset_id"
                def _query():
                    return list(self._testcases_container.query_items(
                        query=query,
                        parameters=[{"name": "@dataset_id", "value": dataset_id}],
                        partition_key=dataset_id
                    ))
                
                test_cases = await asyncio.to_thread(_query)
                
                for tc in test_cases:
                    await asyncio.to_thread(
                        self._testcases_container.delete_item,
                        item=tc['id'],
                        partition_key=dataset_id
                    )
                
                # Delete the dataset
                await asyncio.to_thread(
                    self._datasets_container.delete_item,
                    item=dataset_id,
                    partition_key=dataset_id
                )
                return True
            except exceptions.CosmosResourceNotFoundError:
                return False
    
    return SimpleCosmosService()


async def check_dataset_exists(cosmos_service, dataset_id: str) -> bool:
    """Check if a dataset already exists in Cosmos DB"""
    existing = await cosmos_service.get_dataset(dataset_id)
    return existing is not None


async def upload_contract(cosmos_service, contract: EvaluatorContract, force: bool = False) -> Dict[str, Any]:
    """Upload a single EvaluatorContract to Cosmos DB"""
    dataset_id = contract.id
    
    # Check if dataset already exists
    exists = await check_dataset_exists(cosmos_service, dataset_id)
    if exists and not force:
        return {
            "dataset_id": dataset_id,
            "status": "skipped",
            "reason": "Dataset already exists (use --force to overwrite)",
            "test_cases": 0
        }
    
    try:
        # If force mode and dataset exists, delete it first
        if exists and force:
            await cosmos_service.delete_dataset(dataset_id)
            print(f"  Deleted existing dataset: {dataset_id}")
        
        # Use the cosmos service's create_dataset method which handles EvaluatorContract
        # This will automatically separate dataset from test cases
        stored_dataset = await cosmos_service.create_dataset(contract)
        
        return {
            "dataset_id": stored_dataset["id"],
            "status": "uploaded",
            "reason": "Successfully uploaded",
            "test_cases": len(stored_dataset["test_case_ids"])
        }
    
    except Exception as e:
        return {
            "dataset_id": dataset_id,
            "status": "failed",
            "reason": f"Upload failed: {str(e)}",
            "test_cases": 0
        }


async def process_files(eval_dir: Path, file_filter: str = None, dry_run: bool = False, force: bool = False):
    """Process all JSON files in the evaluation data directory structure"""
    
    # Find JSON files to process
    if file_filter:
        json_files = [eval_dir / file_filter]
        if not json_files[0].exists():
            print(f"❌ File not found: {json_files[0]}")
            return
    else:
        # Process evaluation data structure: recursively find all JSON files
        json_files = list(eval_dir.rglob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {eval_dir}")
        return
    
    print(f"Found {len(json_files)} JSON file(s) to process:")
    for f in json_files:
        # Show the relative path from eval_dir for better organization
        relative_path = f.relative_to(eval_dir)
        print(f"  - {relative_path}")
    print()
    
    # Validate configuration
    print("Configuration:")
    print(f"  Cosmos endpoint: {COSMOS_ENDPOINT}")
    print(f"  Database: {COSMOS_DATABASE}")
    print(f"  Datasets container: {COSMOS_DATASETS_CONTAINER}")
    print(f"  Test cases container: {COSMOS_TESTCASES_CONTAINER}")
    print(f"  Dry run: {dry_run}")
    print(f"  Force overwrite: {force}")
    print()
    
    if not COSMOS_ENDPOINT:
        print("❌ COSMOS_ENDPOINT not configured. Check your .env file.")
        return
    
    # Initialize Cosmos service
    cosmos_service = create_cosmos_service()
    
    # Process each file
    results = []
    total_test_cases = 0
    
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        
        try:
            # Load and validate the file
            contract = await load_sample_file(json_file)
            print(f"  ✅ Loaded dataset: {contract.id}")
            print(f"  📊 Test cases: {len(contract.test_cases)}")
            print(f"  📝 Description: {contract.seed.name}")
            
            if dry_run:
                result = {
                    "dataset_id": contract.id,
                    "status": "dry-run",
                    "reason": "Would be uploaded (dry run mode)",
                    "test_cases": len(contract.test_cases)
                }
            else:
                # Upload to Cosmos DB
                result = await upload_contract(cosmos_service, contract, force)
            
            results.append(result)
            total_test_cases += result["test_cases"]
            
            # Print status
            status_emoji = {
                "uploaded": "✅",
                "skipped": "⏭️ ",
                "failed": "❌",
                "dry-run": "🔍"
            }
            print(f"  {status_emoji.get(result['status'], '❓')} {result['status'].upper()}: {result['reason']}")
            
        except Exception as e:
            print(f"  ❌ FAILED: {str(e)}")
            results.append({
                "dataset_id": json_file.stem,
                "status": "failed",
                "reason": str(e),
                "test_cases": 0
            })
        
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    status_counts = {}
    for result in results:
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"{status.capitalize()}: {count}")
    
    print(f"Total test cases processed: {total_test_cases}")
    
    if dry_run:
        print("\n🔍 This was a dry run. No data was actually uploaded.")
        print("Run without --dry-run to perform the actual upload.")


async def main():
    parser = argparse.ArgumentParser(
        description="Upload evaluation datasets to Cosmos DB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be uploaded without actually uploading"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Overwrite existing datasets with the same ID"
    )
    parser.add_argument(
        "--file", 
        type=str, 
        help="Process only a specific file instead of all files in the directory"
    )
    
    args = parser.parse_args()
    
    # Always process evaluation data from data/eval directory
    script_dir = Path(__file__).parent
    eval_dir = script_dir.parent.parent / "data" / "eval"
    
    if not eval_dir.exists():
        print(f"❌ Evaluation data directory not found: {eval_dir}")
        print("Make sure the data/eval directory exists with evaluation datasets.")
        sys.exit(1)
    
    print("🚀 Cosmos DB Preload Script - Evaluation Data")
    print("=" * 60)
    
    await process_files(eval_dir, args.file, args.dry_run, args.force)


if __name__ == "__main__":
    asyncio.run(main())