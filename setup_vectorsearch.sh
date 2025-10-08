#!/bin/bash
# GCP Vector Search Setup Script
# This script creates a Vector Search index for emotion history

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${VECTOR_SEARCH_INDEX_REGION:-us-central1}"
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

# Create Vector Search Index
echo "Creating Vector Search Index..."
INDEX_ID=$(gcloud ai indexes create \
  --display-name="$INDEX_DISPLAY_NAME" \
  --description="Index for storing emotion history interactions" \
  --region="$REGION" \
  --metadata-file=<(cat <<EOF
{
  "contentsDeltaUri": "gs://$BUCKET_NAME/initial",
  "config": {
    "dimensions": $DIMENSIONS,
    "approximateNeighborsCount": 10,
    "distanceMeasureType": "COSINE_DISTANCE",
    "algorithmConfig": {
      "treeAhConfig": {
        "leafNodeEmbeddingCount": 1000,
        "leafNodesToSearchPercent": 10
      }
    }
  }
}
EOF
) \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Index created with ID: $INDEX_ID"

# Create Index Endpoint
echo "Creating Index Endpoint..."
ENDPOINT_ID=$(gcloud ai index-endpoints create \
  --display-name="$ENDPOINT_DISPLAY_NAME" \
  --region="$REGION" \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Endpoint created with ID: $ENDPOINT_ID"

# Wait for index to be created (this can take a few minutes)
echo "Waiting for index to be ready..."
for i in {1..30}; do
    STATE=$(gcloud ai indexes describe "$INDEX_ID" --region="$REGION" --format="value(state)")
    if [ "$STATE" = "READY" ]; then
        echo "Index is ready!"
        break
    fi
    echo "Index state: $STATE (attempt $i/30)"
    sleep 10
done

# Deploy index to endpoint
echo "Deploying index to endpoint..."
DEPLOYED_INDEX_ID="emotion_history_deployed"
gcloud ai index-endpoints deploy-index "$ENDPOINT_ID" \
  --region="$REGION" \
  --index="$INDEX_ID" \
  --deployed-index-id="$DEPLOYED_INDEX_ID" \
  --display-name="Emotion History Deployed Index" \
  --machine-type="n1-standard-2" \
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
