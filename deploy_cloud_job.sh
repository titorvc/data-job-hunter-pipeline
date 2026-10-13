#!/bin/bash
set -e

PROJECT_ID="data-hunter-494609"
REGION="us-central1"
JOB_NAME="job-hunter-pipeline"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}:latest"

echo "========================================================"
echo "🚀 Desplegando Data Job Hunter a Google Cloud Run Jobs"
echo "========================================================"

echo "1. Construyendo y subiendo imagen con Google Cloud Build..."
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID} -f Dockerfile.cloud .

echo "2. Creando / Actualizando Cloud Run Job..."
gcloud run jobs deploy ${JOB_NAME} \
    --image=${IMAGE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --set-env-vars=GROQ_API_KEY="${GROQ_API_KEY}",SMTP_USER="${SMTP_USER}",SMTP_PASS="${SMTP_PASS}",GCP_PROJECT_ID="${PROJECT_ID}" \
    --memory=1Gi \
    --cpu=1 \
    --max-retries=2 \
    --task-timeout=15m

echo "3. Configurando Cloud Scheduler para ejecucion automatica 2 veces al dia..."
gcloud scheduler jobs create http ${JOB_NAME}-trigger \
    --location=${REGION} \
    --schedule="0 13,22 * * *" \
    --time-zone="UTC" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID} || \
gcloud scheduler jobs update http ${JOB_NAME}-trigger \
    --location=${REGION} \
    --schedule="0 13,22 * * *" \
    --time-zone="UTC" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=${PROJECT_ID}

echo "========================================================"
echo "✅ Despliegue completado con éxito."
echo "Para ejecutar una prueba manual en la nube:"
echo "gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo "========================================================"
