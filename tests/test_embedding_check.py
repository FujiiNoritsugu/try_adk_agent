#!/usr/bin/env python3
"""Check if embeddings are being generated correctly"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from vectorsearch.embedder import EmotionEmbedder, TouchInput, Emotion

# Create embedder
embedder = EmotionEmbedder()

print(f"Project ID: {embedder.project_id}")
print(f"Location: {embedder.location}")
print(f"Model initialized: {embedder.model is not None}")

# Test embedding generation
touch_input = TouchInput(
    data=0.7,
    touched_area="頭",
    gesture_type="pat",
    hand_velocity=180.0
)

emotion = Emotion(joy=4.5, fun=3.5, anger=0.2, sad=0.1)

# Create interaction record
record = embedder.create_interaction_record(
    input_data=touch_input,
    emotion=emotion,
    response_text="テスト用の応答",
    session_id="test"
)

print(f"\nRecord ID: {record.id}")
print(f"Embedding length: {len(record.embedding)}")
print(f"First 10 values: {record.embedding[:10]}")

# Check if all zeros
all_zeros = all(v == 0.0 for v in record.embedding)
print(f"All zeros: {all_zeros}")

if all_zeros:
    print("\n⚠️  WARNING: Embedding is all zeros (mock mode)!")
    print("   This means Vertex AI Text Embedding is not working properly.")
else:
    print("\n✓ Embedding looks good (contains non-zero values)")
