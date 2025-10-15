#!/bin/bash
# GCP Vector Search Setup Script
# This script creates a Vector Search index for emotion history

set -e

# Configuration
PROJECT_ID="your-project-id"  # Replace with your GCP project ID or set via env variable
REGION="your-region"       # e.g., us-central1
INDEX_NAME="emotion-history-index"
INDEX_DISPLAY_NAME="Emotion History Index"
ENDPOINT_DISPLAY_NAME="Emotion History Endpoint"
DIMENSIONS=768

echo "=================================================="
echo "GCP Vector Search Setup"
echo "=================================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Index Name: $INDEX_NAME"
echo "Dimensions: $DIMENSIONS"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if project ID is set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "Error: Please set GOOGLE_CLOUD_PROJECT environment variable"
    echo "Example: export GOOGLE_CLOUD_PROJECT=your-actual-project-id"
    exit 1
fi

# Set active project
echo "Setting active project..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com

# Create GCS bucket for index data (if not exists)
BUCKET_NAME="${PROJECT_ID}-vectorsearch-data"
echo "Creating GCS bucket: gs://$BUCKET_NAME"
gsutil mb -l "$REGION" "gs://$BUCKET_NAME" 2>/dev/null || echo "Bucket already exists"

# Create Vector Search Index with STREAM_UPDATE
echo "Creating Vector Search Index with streaming update capability..."
CREATE_OUTPUT=$(gcloud ai indexes create \
  --display-name="$INDEX_DISPLAY_NAME" \
  --description="Index for storing emotion history interactions with streaming updates" \
  --region="$REGION" \
  --metadata-file=<(cat <<EOF
{
  "config": {
    "dimensions": $DIMENSIONS,
    "approximateNeighborsCount": 10,
    "distanceMeasureType": "COSINE_DISTANCE",
    "shardSize": "SHARD_SIZE_SMALL",
    "algorithmConfig": {
      "treeAhConfig": {
        "leafNodeEmbeddingCount": 1000,
        "leafNodesToSearchPercent": 10
      }
    }
  },
  "indexUpdateMethod": "STREAM_UPDATE"
}
EOF
) \
  --format="value(name)")

# Extract index ID and operation ID from output
INDEX_ID=$(echo "$CREATE_OUTPUT" | awk -F'/' '{print $6}')
OPERATION_ID=$(echo "$CREATE_OUTPUT" | awk -F'/' '{print $8}')

echo "Index ID: $INDEX_ID"
echo "Operation ID: $OPERATION_ID"

# Create Index Endpoint
echo "Creating Index Endpoint..."
ENDPOINT_ID=$(gcloud ai index-endpoints create \
  --display-name="$ENDPOINT_DISPLAY_NAME" \
  --region="$REGION" \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Endpoint created with ID: $ENDPOINT_ID"

# Wait for index creation operation to complete
echo "Waiting for index creation to complete..."
for i in {1..60}; do
    STATE=$(gcloud ai operations describe "$OPERATION_ID" \
        --index="$INDEX_ID" \
        --region="$REGION" \
        --format="value(done)" 2>/dev/null || echo "false")

    if [ "$STATE" = "True" ]; then
        echo "Index creation completed!"
        break
    fi
    echo "Waiting for operation to complete (attempt $i/60)..."
    sleep 10
done

# Verify index is ready
echo "Verifying index status..."
STATE=$(gcloud ai indexes describe "$INDEX_ID" --region="$REGION" --format="value(state)" 2>/dev/null || echo "UNKNOWN")
echo "Index state: $STATE"

if [ "$STATE" != "READY" ]; then
    echo "Warning: Index is not yet ready. Current state: $STATE"
    echo "You may need to wait longer and check status with:"
    echo "  gcloud ai indexes describe $INDEX_ID --region=$REGION"
fi

# Deploy index to endpoint
echo "Deploying index to endpoint..."
DEPLOYED_INDEX_ID="emotion_history_deployed"
gcloud ai index-endpoints deploy-index "$ENDPOINT_ID" \
  --region="$REGION" \
  --index="$INDEX_ID" \
  --deployed-index-id="$DEPLOYED_INDEX_ID" \
  --display-name="Emotion History Deployed Index" \
  --machine-type="e2-standard-2" \
  --min-replica-count=1 \
  --max-replica-count=2

echo "=================================================="
echo "Setup completed successfully!"
echo "=================================================="
echo ""
echo "Add these to your .env file:"
echo ""
echo "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "VECTOR_SEARCH_INDEX_ID=$INDEX_ID"
echo "VECTOR_SEARCH_ENDPOINT_ID=$ENDPOINT_ID"
echo "VECTOR_SEARCH_DEPLOYED_INDEX_ID=$DEPLOYED_INDEX_ID"
echo "VECTOR_SEARCH_INDEX_REGION=$REGION"
echo "VECTOR_SEARCH_BUCKET=gs://$BUCKET_NAME"
echo ""
echo "=================================================="
