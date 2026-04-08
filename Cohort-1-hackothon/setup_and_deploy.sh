#!/bin/bash
set -e

# Point gcloud to its own bundled Python 3.12 (avoids Windows Store alias conflict)
export CLOUDSDK_PYTHON="/c/Users/srsmu/AppData/Local/Google/Cloud SDK/google-cloud-sdk/platform/bundledpython/python.exe"
export PATH="/c/Google-ADK-AI-Agents/Cohort-1-hackothon/.venv/Scripts:$PATH"

set -a
source /c/Google-ADK-AI-Agents/Cohort-1-hackothon/productivity_assistant/.env
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
    sqladmin.googleapis.com \
    servicenetworking.googleapis.com \
    --project=$PROJECT_ID

echo ""
echo "========== Creating Cloud SQL PostgreSQL instance =========="
gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --project=$PROJECT_ID || echo "Instance may already exist, continuing..."

echo ""
echo "========== Creating database =========="
gcloud sql databases create productivity \
    --instance=$DB_INSTANCE_NAME \
    --project=$PROJECT_ID || echo "Database may already exist, continuing..."

echo ""
echo "========== Setting DB password =========="
gcloud sql users set-password postgres \
    --instance=$DB_INSTANCE_NAME \
    --password=$DB_PASSWORD \
    --project=$PROJECT_ID

# Schema is initialised automatically by agent.py on first startup (no psql needed)

echo ""
echo "========== Creating service account =========="
gcloud iam service-accounts create $SA_NAME \
    --display-name="Service Account for Productivity Assistant" \
    --project=$PROJECT_ID || echo "SA may already exist, continuing..."

echo ""
echo "========== Granting IAM roles =========="
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudsql.client"

echo ""
echo "========== Deploying agent to Cloud Run =========="
cd /c/Google-ADK-AI-Agents/Cohort-1-hackothon

uvx --from google-adk==1.27.2 adk deploy cloud_run \
    --project=$PROJECT_ID \
    --region=us-central1 \
    --service_name=productivity-assistant \
    --with_ui \
    ./productivity_assistant \
    -- \
    --labels=dev-hackathon=use-adk \
    --service-account=$SERVICE_ACCOUNT \
    --add-cloudsql-instances=$PROJECT_ID:us-central1:$DB_INSTANCE_NAME \
    --set-env-vars="DATABASE_URL=postgresql://postgres:$DB_PASSWORD@/productivity?host=/cloudsql/$PROJECT_ID:us-central1:$DB_INSTANCE_NAME" \
    --allow-unauthenticated \
    --min-instances=1

echo ""
echo "========== Done! =========="
echo "Your agent is live. Get the URL with:"
echo "gcloud run services describe productivity-assistant --region=us-central1 --format='value(status.url)'"
