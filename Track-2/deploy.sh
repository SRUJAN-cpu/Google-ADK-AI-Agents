#!/bin/bash
set -a
source /c/Google-ADK-AI-Agents/Track-2/weather_decision_agent/.env
set +a

cd /c/Google-ADK-AI-Agents/Track-2

uvx --from google-adk==1.27.2 adk deploy cloud_run --project=$PROJECT_ID --region=us-central1 --service_name=weather-decision-agent --with_ui ./weather_decision_agent -- --labels=dev-hackathon=use-adk --service-account=$SERVICE_ACCOUNT
