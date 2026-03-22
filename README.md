# 1. **Set your Project** 
    gcloud config set project [PROJECT_ID]

# 2. **Enable required APIs**
    gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com

# **Introducing the APIs**

_Cloud Run Admin API (run.googleapis.com)_ allows you to run frontend and backend services, batch jobs, or websites in a fully managed environment. It handles the infrastructure for deploying and scaling your containerized applications.
_Artifact Registry API (artifactregistry.googleapis.com)_ provides a secure, private repository to store your container images. It is the evolution of Container Registry and integrates seamlessly with Cloud Run and Cloud Build.
_Cloud Build API (cloudbuild.googleapis.com)_ is a serverless CI/CD platform that executes your builds on Google Cloud infrastructure. It is used to build your container image in the cloud from your Dockerfile.
_Vertex AI API (aiplatform.googleapis.com)_ enables your deployed application to communicate with Gemini models to perform core AI tasks. It provides the unified API for all of Google Cloud's AI services.
_Compute Engine API (compute.googleapis.com)_ provides secure and customizable virtual machines that run on Google's infrastructure. While Cloud Run is managed, the Compute Engine API is often required as a foundational dependency for various networking and compute resources

# 3. **Prepare the Dev environment**
   Create and activate a virtual environment (Maybe using uv or by any type required)
   Install the required packages into your virtual environment.
     `uv pip install -r requirements.txt`

# 4. **Set up environment variables**
    1. Set the variables in your terminal first
      PROJECT_ID=$(gcloud config get-value project)
      PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
      SA_NAME=Service_name

    2. Create the .env file using those variables
      cat <<EOF > .env
      PROJECT_ID=$PROJECT_ID
      PROJECT_NUMBER=$PROJECT_NUMBER
      SA_NAME=$SA_NAME
      SERVICE_ACCOUNT=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
      MODEL="gemini-2.5-flash"
      EOF

   **NOTE**
     Check the .env file and make sure both PROJECT_ID, PROJECT_NUMBER, and SERVICE_ACCOUNT have been assigned values. If project details are missing, find them by running gcloud projects list.
     If the service account is missing, you can list the accounts in your project to find the email address (it should end in .iam.gserviceaccount.com) by running: gcloud iam service-accounts list.

# 5. **Create agent workflow**
   For example refer
     `https://github.com/SRUJAN-cpu/AI-agents-using-Google-ADK/blob/main/adk_and_a2a/illustration_agent/agent.py`

# 6. **Prepare the app for deployment**
   Set up IAM permissions
    With the local code ready,
        1. In the terminal, load the variables into your shell session.
            `source .env`
            
   **Note:** If the Cloud Shell session refreshes or you open a new terminal tab, you may need to run source .env again to reload these variables.
        2. Create a dedicated service account for your Cloud Run service.
            _so that it has its own specific permission_
                `gcloud iam service-accounts create ${SA_NAME} \
                    --display-name="Service Account for this agent "`
        > By creating a dedicated identity for this specific application, you ensure the agent only has the exact permissions it needs, rather than using a default account with overly broad access.
        3. Grant the service account the Vertex AI User role, which gives it permission to call Google's models.
            `# Grant the "Vertex AI User" role to your service account
                gcloud projects add-iam-policy-binding $PROJECT_ID \
                  --member="serviceAccount:$SERVICE_ACCOUNT" \
                  --role="roles/aiplatform.user"`

# 7. **Depoly the agent using the ADK CLI** 
    # Run the deployment command
    uvx --from google-adk==1.14.0 \
    adk deploy cloud_run \
      --project=$PROJECT_ID \
      --region=europe-west1 \
      --service_name=zoo-tour-guide \
      --with_ui \
      . \
      -- \
      --labels=dev-tutorial=codelab-adk \
      --service-account=$SERVICE_ACCOUNT
IF prompted for Y/N: Hit (Y)

# 8. **Test and enjoy 🥳**

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
One more way of running the agent
Follow the above 1st and 2nd step
# 3. Create project directory and navigate into it:
    mkdir ai-agents-adk
    cd ai-agents-adk

# 4. Create and activate a virtual environment:
    uv venv --python 3.12
    source .venv/bin/activate

# 5. Install adk page
    uv pip install google-adk

# 6. Create your agent
    adk create <your-agent-name>
    CHOOSE YOUR CHOICE WHEN PROMPTS SHOWS UP

# 7. Run your agent in termnial or web:
    # terminal 
    adk run <<your-agent-name>
    # web
    adk run
