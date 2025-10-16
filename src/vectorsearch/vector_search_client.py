#!/usr/bin/env python3
"""
Vector Search Client for querying and managing emotion history
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dataclasses import asdict

try:
    from google.cloud import aiplatform
    from google.cloud import aiplatform_v1
    from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint

    AIPLATFORM_AVAILABLE = True
except ImportError:
    AIPLATFORM_AVAILABLE = False
    logging.warning(
        "AI Platform SDK not installed. Install with: pip install google-cloud-aiplatform"
    )

from .embedder import InteractionRecord

logger = logging.getLogger(__name__)


class VectorSearchClient:
    """Client for Vector Search operations"""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        index_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        deployed_index_id: Optional[str] = None,
    ):
        """
        Initialize Vector Search client

        Args:
            project_id: GCP Project ID
            location: GCP region
            index_id: Vector Search Index ID
            endpoint_id: Vector Search Endpoint ID
            deployed_index_id: Deployed Index ID
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv(
            "VECTOR_SEARCH_INDEX_REGION", "us-central1"
        )
        self.index_id = index_id or os.getenv("VECTOR_SEARCH_INDEX_ID")
        self.endpoint_id = endpoint_id or os.getenv("VECTOR_SEARCH_ENDPOINT_ID")
        self.deployed_index_id = deployed_index_id or os.getenv(
            "VECTOR_SEARCH_DEPLOYED_INDEX_ID"
        )

        self.index_endpoint = None
        self.index_client = None
        self.use_mock = False

        if not AIPLATFORM_AVAILABLE:
            logger.warning("AI Platform not available. Using mock mode.")
            self.use_mock = True
            return

        if not all([self.project_id, self.index_id, self.endpoint_id]):
            logger.warning("Vector Search not configured. Using mock mode.")
            logger.warning(
                "Set: GOOGLE_CLOUD_PROJECT, VECTOR_SEARCH_INDEX_ID, VECTOR_SEARCH_ENDPOINT_ID"
            )
            self.use_mock = True
            return

        try:
            # Initialize AI Platform
            aiplatform.init(project=self.project_id, location=self.location)

            # Get Index Endpoint
            self.index_endpoint = MatchingEngineIndexEndpoint(
                index_endpoint_name=f"projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.endpoint_id}"
            )

            # Initialize Index Service Client for streaming updates
            self.index_client = aiplatform_v1.IndexServiceClient(
                client_options={
                    "api_endpoint": f"{self.location}-aiplatform.googleapis.com"
                }
            )

            logger.info("Vector Search client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vector Search: {e}")
            logger.warning("Falling back to mock mode")
            self.use_mock = True

    def search_similar(
        self, query_embedding: List[float], top_k: int = 5, threshold: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar interactions

        Args:
            query_embedding: Query vector (768 dimensions)
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of similar interaction records
        """
        if self.use_mock:
            logger.info("Using mock search results")
            return self._mock_search_results()

        try:
            # Perform vector search
            response = self.index_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k,
            )

            results = []
            for neighbor in response[0]:
                # Filter by threshold
                if neighbor.distance >= threshold:
                    results.append(
                        {
                            "id": neighbor.id,
                            "distance": neighbor.distance,
                            "metadata": (
                                neighbor.metadata
                                if hasattr(neighbor, "metadata")
                                else {}
                            ),
                        }
                    )

            logger.info(f"Found {len(results)} similar interactions")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def upsert_interaction(self, record: InteractionRecord) -> bool:
        """
        Insert or update an interaction record using streaming API

        Args:
            record: Interaction record to upsert

        Returns:
            Success status
        """
        if self.use_mock:
            logger.info(f"Mock upsert: {record.id}")
            return True

        if not self.index_client:
            logger.error("Index client not initialized")
            return False

        try:
            logger.info(f"Upserting interaction via streaming API: {record.id}")

            # Create IndexDatapoint with embedding
            datapoint = aiplatform_v1.IndexDatapoint(
                datapoint_id=record.id, feature_vector=record.embedding
            )

            # Create the full index resource name
            index_name = f"projects/{self.project_id}/locations/{self.location}/indexes/{self.index_id}"

            # Create upsert request
            upsert_request = aiplatform_v1.UpsertDatapointsRequest(
                index=index_name, datapoints=[datapoint]
            )

            # Execute upsert
            response = self.index_client.upsert_datapoints(request=upsert_request)

            logger.info(f"Successfully upserted interaction: {record.id}")
            return True

        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            return False

    def _mock_search_results(self) -> List[Dict]:
        """Generate mock search results for testing"""
        return [
            {
                "id": "interaction_20251009_050000_0001",
                "distance": 0.85,
                "metadata": {
                    "timestamp": "2025-10-09T05:00:00Z",
                    "input": {"touched_area": "頭", "data": 0.6, "gesture_type": "tap"},
                    "emotion": {"joy": 4.0, "fun": 3.0, "anger": 0.5, "sad": 0.3},
                    "response_text": "優しく頭を触ってくれて嬉しいな",
                },
            },
            {
                "id": "interaction_20251009_045500_0002",
                "distance": 0.78,
                "metadata": {
                    "timestamp": "2025-10-09T04:55:00Z",
                    "input": {
                        "touched_area": "頭",
                        "data": 0.4,
                        "gesture_type": "swipe",
                    },
                    "emotion": {"joy": 3.5, "fun": 2.8, "anger": 0.3, "sad": 0.5},
                    "response_text": "気持ちいいなぁ...もっと撫でて",
                },
            },
        ]

    def get_stats(self) -> Dict:
        """
        Get statistics about stored interactions

        Returns:
            Statistics dictionary including total vector count
        """
        if self.use_mock:
            return {"total_interactions": 42, "mode": "mock", "index_configured": False}

        try:
            # Get the MatchingEngineIndex resource to access stats
            index = MatchingEngineIndex(
                index_name=f"projects/{self.project_id}/locations/{self.location}/indexes/{self.index_id}"
            )

            # Access index stats from the underlying GCA resource
            vectors_count = 0
            shards_count = 0

            if hasattr(index, "_gca_resource") and index._gca_resource:
                if (
                    hasattr(index._gca_resource, "index_stats")
                    and index._gca_resource.index_stats
                ):
                    vectors_count = index._gca_resource.index_stats.vectors_count or 0
                    shards_count = index._gca_resource.index_stats.shards_count or 0

            return {
                "total_interactions": int(vectors_count) if vectors_count else 0,
                "vectors_count": int(vectors_count) if vectors_count else 0,
                "shards_count": shards_count,
                "mode": "production",
                "index_configured": True,
                "index_id": self.index_id,
                "endpoint_id": self.endpoint_id,
                "project_id": self.project_id,
                "location": self.location,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e), "mode": "production", "index_configured": True}


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv

    load_dotenv()
    # Create client
    client = VectorSearchClient()

    # Test search with mock embedding
    mock_embedding = [0.1] * 768
    results = client.search_similar(mock_embedding, top_k=3)

    print(f"\nSearch Results: {len(results)} found")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. ID: {result['id']}")
        print(f"   Distance: {result['distance']:.2f}")
        if "metadata" in result and "response_text" in result["metadata"]:
            print(f"   Response: {result['metadata']['response_text']}")

    # Get stats
    stats = client.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
