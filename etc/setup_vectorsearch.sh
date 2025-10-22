#!/bin/bash
# GCP Vector Search Setup Script
# This script creates a Vector Search index for emotion history

set -e

# Configuration
PROJECT_ID="gen-lang-client-0471694923"  # Replace with your GCP project ID or set via env variable
REGION="asia-northeast1"       # e.g., us-central1
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
gcloud ai indexes create \
  --display-name="$INDEX_DISPLAY_NAME" \
  --description="Index for storing emotion history interactions with streaming updates" \
  --region="$REGION" \
  --index-update-method=stream_update \
  --metadata-file=<(cat <<EOF
{
  "contentsDeltaUri": "gs://$BUCKET_NAME/initial",
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
  }
}
EOF
)

# Get the most recently created index
echo "Retrieving index information..."
INDEX_INFO=$(gcloud ai indexes list --region="$REGION" --sort-by="~createTime" --limit=1 --format="value(name)")
INDEX_ID=$(echo "$INDEX_INFO" | awk -F'/' '{print $NF}')

echo "Index ID: $INDEX_ID"

# Create Index Endpoint
echo "Creating Index Endpoint..."
gcloud ai index-endpoints create \
  --display-name="$ENDPOINT_DISPLAY_NAME" \
  --region="$REGION"

# Get the most recently created endpoint
echo "Retrieving endpoint information..."
ENDPOINT_INFO=$(gcloud ai index-endpoints list --region="$REGION" --sort-by="~createTime" --limit=1 --format="value(name)")
ENDPOINT_ID=$(echo "$ENDPOINT_INFO" | awk -F'/' '{print $NF}')

echo "Endpoint created with ID: $ENDPOINT_ID"

# Wait for index creation to complete
echo "Waiting for index creation to complete..."
for i in {1..60}; do
    STATE=$(gcloud ai indexes describe "$INDEX_ID" \
        --region="$REGION" \
        --format="value(name)" 2>/dev/null)

    if [ -n "$STATE" ]; then
        echo "Index is available!"
        break
    fi
    echo "Waiting for index to be available (attempt $i/60)..."
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
DEPLOYED_INDEX_ID="emotion_history_deployed_$(date +%Y%m%d_%H%M%S)"
echo "Using deployed index ID: $DEPLOYED_INDEX_ID"
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
