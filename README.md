1. **Set your Project** 
    `gcloud config set project [PROJECT_ID]`

2. **Enable required APIs **
    `gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com`

**Introducing the APIs**

_Cloud Run Admin API (run.googleapis.com)_ allows you to run frontend and backend services, batch jobs, or websites in a fully managed environment. It handles the infrastructure for deploying and scaling your containerized applications.
_Artifact Registry API (artifactregistry.googleapis.com)_ provides a secure, private repository to store your container images. It is the evolution of Container Registry and integrates seamlessly with Cloud Run and Cloud Build.
_Cloud Build API (cloudbuild.googleapis.com)_ is a serverless CI/CD platform that executes your builds on Google Cloud infrastructure. It is used to build your container image in the cloud from your Dockerfile.
_Vertex AI API (aiplatform.googleapis.com)_ enables your deployed application to communicate with Gemini models to perform core AI tasks. It provides the unified API for all of Google Cloud's AI services.
_Compute Engine API (compute.googleapis.com)_ provides secure and customizable virtual machines that run on Google's infrastructure. While Cloud Run is managed, the Compute Engine API is often required as a foundational dependency for various networking and compute resources

3. **Prepare the Dev environment**
   Create and activate a virtual environment (Maybe using uv or by any type required)
   Install the required packages into your virtual environment.
     `uv pip install -r requirements.txt`

4. **Set up environment variables**
   # 1. Set the variables in your terminal first
     `PROJECT_ID=$(gcloud config get-value project)
      PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
      SA_NAME=Service_name`

   # 2. Create the .env file using those variables
     `cat <<EOF > .env
      PROJECT_ID=$PROJECT_ID
      PROJECT_NUMBER=$PROJECT_NUMBER
      SA_NAME=$SA_NAME
      SERVICE_ACCOUNT=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
      MODEL="gemini-2.5-flash"
      EOF`

   **NOTE**
     Check the .env file and make sure both PROJECT_ID, PROJECT_NUMBER, and SERVICE_ACCOUNT have been assigned values. If project details are missing, find them by running gcloud projects list.
     If the service account is missing, you can list the accounts in your project to find the email address (it should end in .iam.gserviceaccount.com) by running: gcloud iam service-accounts list.

5. **Create agent workflow**
     For example refer ---> https://github.com/SRUJAN-cpu/AI-agents-using-Google-ADK/blob/main/adk_and_a2a/illustration_agent/agent.py 
