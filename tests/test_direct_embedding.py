#!/usr/bin/env python3
"""Test direct embedding generation"""

from dotenv import load_dotenv
load_dotenv()

import vertexai
from vertexai.language_models import TextEmbeddingModel

project_id = "gen-lang-client-0471694923"
location = "us-central1"

print(f"Initializing Vertex AI: project={project_id}, location={location}")
vertexai.init(project=project_id, location=location)

print("Loading model: textembedding-gecko@003")
model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")

text = "テスト用のテキスト"
print(f"Generating embedding for: {text}")

try:
    embeddings = model.get_embeddings([text])
    embedding = embeddings[0].values

    print(f"\n✓ Success!")
    print(f"Embedding length: {len(embedding)}")
    print(f"First 10 values: {embedding[:10]}")

    all_zeros = all(v == 0.0 for v in embedding)
    print(f"All zeros: {all_zeros}")

except Exception as e:
    print(f"\n✗ Failed: {e}")
