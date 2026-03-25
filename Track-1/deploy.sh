#!/bin/bash
set -a
source /c/Google-ADK-AI-Agents/Track-1/summerizing_agent/.env
set +a

cd /c/Google-ADK-AI-Agents/Track-1

uvx --from google-adk==1.27.2 adk deploy cloud_run --project=$PROJECT_ID --region=us-central1 --service_name=summerizing-guide --with_ui ./summerizing_agent -- --labels=dev-hackathon=use-adk --service-account=$SERVICE_ACCOUNT

