#!/bin/bash
set -a
source /c/Google-ADK-AI-Agents/Track-2/weather_decision_agent/.env
set +a

echo "========== gcloud auth =========="
gcloud auth list

echo ""
echo "========== active project =========="
gcloud config get-value project

echo ""
echo "========== setting project =========="
gcloud config set project $PROJECT_ID
gcloud config get-value project

echo ""
echo "========== required APIs status =========="
gcloud services list --enabled --project=$PROJECT_ID --filter="name:(run.googleapis.com OR artifactregistry.googleapis.com OR cloudbuild.googleapis.com OR aiplatform.googleapis.com)" --format="table(name,state)"

echo ""
echo "========== service account exists? =========="
gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID 2>&1

echo ""
echo "========== service account IAM roles =========="
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:$SERVICE_ACCOUNT" \
  --format="table(bindings.role)" 2>&1
