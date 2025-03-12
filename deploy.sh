#!/bin/bash

# Configuration
PROJECT_ID="power-watch-449503"  # Google Cloud project ID
REGION="us-west1"            # Replace with your preferred region
SERVICE_NAME="pge-bill-analyzer"

# Build the container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}"
