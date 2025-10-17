#!/usr/bin/env python3
"""
Add test data to Vector Search index
"""

import logging
from dotenv import load_dotenv

from vectorsearch.embedder import EmotionEmbedder, TouchInput, Emotion
from vectorsearch.vector_search_client import VectorSearchClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create embedder and client
embedder = EmotionEmbedder(location="asia-northeast1")
client = VectorSearchClient()

# Test data samples
test_samples = [
    {
        "touch": TouchInput(data=0.6, touched_area="頭", gesture_type="tap", hand_velocity=150.5),
        "emotion": Emotion(joy=4.0, fun=3.0, anger=0.5, sad=0.3),
        "response": "優しく頭を触ってくれて嬉しいな"
    },
    {
        "touch": TouchInput(data=0.4, touched_area="頭", gesture_type="stroke", hand_velocity=80.0),
        "emotion": Emotion(joy=3.5, fun=2.8, anger=0.3, sad=0.5),
        "response": "気持ちいいなぁ...もっと撫でて"
    },
    {
        "touch": TouchInput(data=0.8, touched_area="背中", gesture_type="pat", hand_velocity=200.0),
        "emotion": Emotion(joy=2.0, fun=1.5, anger=2.5, sad=1.0),
        "response": "ちょっと強いよ...優しくして"
    },
    {
        "touch": TouchInput(data=0.5, touched_area="手", gesture_type="hold", hand_velocity=50.0),
        "emotion": Emotion(joy=4.5, fun=2.0, anger=0.2, sad=0.1),
        "response": "手を繋いでくれて嬉しい！"
    },
    {
        "touch": TouchInput(data=0.3, touched_area="肩", gesture_type="tap", hand_velocity=120.0),
        "emotion": Emotion(joy=2.5, fun=3.5, anger=0.5, sad=0.8),
        "response": "どうしたの？何か用？"
    },
]

def main():
    """Add test data to vector search index"""
    logger.info(f"Adding {len(test_samples)} test samples to Vector Search index")

    success_count = 0
    fail_count = 0

    for i, sample in enumerate(test_samples, 1):
        logger.info(f"\n--- Sample {i}/{len(test_samples)} ---")

        # Create interaction record with embedding
        record = embedder.create_interaction_record(
            input_data=sample["touch"],
            emotion=sample["emotion"],
            response_text=sample["response"],
            session_id="test_session_001"
        )

        logger.info(f"Record ID: {record.id}")
        logger.info(f"Embedding dimensions: {len(record.embedding)}")

        # Upsert to Vector Search
        success = client.upsert_interaction(record)

        if success:
            success_count += 1
            logger.info(f"✓ Successfully added: {record.id}")
        else:
            fail_count += 1
            logger.error(f"✗ Failed to add: {record.id}")

    logger.info(f"\n=== Summary ===")
    logger.info(f"Success: {success_count}/{len(test_samples)}")
    logger.info(f"Failed: {fail_count}/{len(test_samples)}")

    # Get stats
    stats = client.get_stats()
    logger.info(f"\nVector Search Stats:")
    logger.info(f"Total vectors: {stats.get('vectors_count', 0)}")
    logger.info(f"Shards: {stats.get('shards_count', 0)}")

if __name__ == "__main__":
    main()
