#!/bin/bash
set -e
set -a
source /c/Google-ADK-AI-Agents/Track-2/weather_decision_agent/.env
set +a

echo "========== Setting project =========="
gcloud config set project $PROJECT_ID

echo ""
echo "========== Enabling required APIs =========="
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID

echo ""
echo "========== Creating service account =========="
gcloud iam service-accounts create $SA_NAME \
    --display-name="Service Account for Weather Decision Agent" \
    --project=$PROJECT_ID

echo ""
echo "========== Granting Vertex AI User role =========="
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user"

echo ""
echo "========== Granting Cloud Run Invoker role =========="
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker"

echo ""
echo "========== Deploying agent =========="
cd /c/Google-ADK-AI-Agents/Track-2

uvx --from google-adk==1.27.2 adk deploy cloud_run \
    --project=$PROJECT_ID \
    --region=us-central1 \
    --service_name=weather-decision-agent \
    --with_ui \
    ./weather_decision_agent \
    -- \
    --labels=dev-hackathon=use-adk \
    --service-account=$SERVICE_ACCOUNT
