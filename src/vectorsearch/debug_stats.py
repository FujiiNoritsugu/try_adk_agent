#!/usr/bin/env python3
"""
Debug script to investigate Vector Search index statistics
"""

import logging
from dotenv import load_dotenv
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("VECTOR_SEARCH_INDEX_REGION", "us-central1")
index_id = os.getenv("VECTOR_SEARCH_INDEX_ID")
endpoint_id = os.getenv("VECTOR_SEARCH_ENDPOINT_ID")

# Initialize AI Platform
aiplatform.init(project=project_id, location=location)

# Get Index
logger.info(f"Getting index: {index_id}")
index = MatchingEngineIndex(
    index_name=f"projects/{project_id}/locations/{location}/indexes/{index_id}"
)

print("\n=== Index Information ===")
print(f"Index Name: {index.display_name}")
print(f"Resource Name: {index.resource_name}")
print(f"Create Time: {index.create_time}")
print(f"Update Time: {index.update_time}")

# Check _gca_resource
if hasattr(index, "_gca_resource") and index._gca_resource:
    gca = index._gca_resource
    print(f"\n=== GCA Resource ===")
    print(f"Name: {gca.name}")
    print(f"Display Name: {gca.display_name}")

    if hasattr(gca, "index_stats") and gca.index_stats:
        print(f"\n=== Index Stats ===")
        print(f"Vectors Count: {gca.index_stats.vectors_count}")
        print(f"Shards Count: {gca.index_stats.shards_count}")
    else:
        print("\n⚠️  No index_stats found in GCA resource")
        print(f"GCA attributes: {dir(gca)}")

    if hasattr(gca, "deployed_indexes"):
        print(f"\n=== Deployed Indexes ===")
        print(f"Count: {len(gca.deployed_indexes)}")
        for di in gca.deployed_indexes:
            print(f"  - {di}")
else:
    print("\n⚠️  No _gca_resource found")

# Get Index Endpoint
logger.info(f"Getting endpoint: {endpoint_id}")
endpoint = MatchingEngineIndexEndpoint(
    index_endpoint_name=f"projects/{project_id}/locations/{location}/indexEndpoints/{endpoint_id}"
)

print("\n=== Endpoint Information ===")
print(f"Endpoint Name: {endpoint.display_name}")
print(f"Resource Name: {endpoint.resource_name}")

if hasattr(endpoint, "_gca_resource") and endpoint._gca_resource:
    endpoint_gca = endpoint._gca_resource
    print(f"\n=== Deployed Indexes on Endpoint ===")
    if hasattr(endpoint_gca, "deployed_indexes"):
        for di in endpoint_gca.deployed_indexes:
            print(f"\nDeployed Index ID: {di.id}")
            print(f"  Index: {di.index}")
            print(f"  Display Name: {di.display_name if hasattr(di, 'display_name') else 'N/A'}")
            if hasattr(di, "index_sync_time"):
                print(f"  Last Sync: {di.index_sync_time}")

# Try direct API call
print("\n=== Direct API Check ===")
try:
    from google.cloud import aiplatform_v1

    index_client = aiplatform_v1.IndexServiceClient(
        client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    )

    index_name = f"projects/{project_id}/locations/{location}/indexes/{index_id}"
    index_response = index_client.get_index(name=index_name)

    print(f"Index response: {index_response}")
    if hasattr(index_response, "index_stats"):
        print(f"Vectors count (direct): {index_response.index_stats.vectors_count}")
    else:
        print("No index_stats in direct response")

except Exception as e:
    logger.error(f"Direct API call failed: {e}")
