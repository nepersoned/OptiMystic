#!/bin/bash
set -e
exec </dev/null
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export CLOUDSDK_CORE_PASS_CREDENTIALS_TO_GSUTIL=false
GCLOUD="/c/Users/kevin/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud"
PROJECT=optimystic-493605
REGION=asia-northeast3
SERVICE=optimystic-api
REPO=optimystic
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/api:latest"

echo "--- [1/5] Setting project ---"
"$GCLOUD" config set project $PROJECT

echo "--- [2/5] Enabling APIs ---"
"$GCLOUD" services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$PROJECT

echo "--- [3/5] Ensuring Artifact Registry repo ---"
if "$GCLOUD" artifacts repositories describe $REPO --location=$REGION --project=$PROJECT &>/dev/null; then
  echo "Repo already exists."
else
  "$GCLOUD" artifacts repositories create $REPO --repository-format=docker --location=$REGION --project=$PROJECT
fi

echo "--- [4/5] Cloud Build (this takes ~5 min) ---"
"$GCLOUD" builds submit --project=$PROJECT --tag "$IMAGE" --file docker/Dockerfile .

echo "--- [5/5] Cloud Run deploy ---"
ENV_VARS=$(grep -v '^#' deploy/gcp/.env.app | grep -v '^$' | paste -sd, -)
"$GCLOUD" run deploy $SERVICE \
  --image="$IMAGE" \
  --region=$REGION \
  --platform=managed \
  --project=$PROJECT \
  --port=8000 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900 \
  --concurrency=4 \
  --no-allow-unauthenticated \
  ${ENV_VARS:+--set-env-vars="$ENV_VARS"}

echo ""
echo "=== DONE ==="
"$GCLOUD" run services describe $SERVICE --region=$REGION --project=$PROJECT --format='value(status.url)'
