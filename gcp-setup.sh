#!/usr/bin/env bash
# gcp-setup.sh
# Automates the cloud setup for GCS model registry, IAM, and GKE dependencies.
# Run this on your host machine with active Google Cloud SDK configurations.

set -eo pipefail

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-ml-model-registry"
SA_NAME="gke-model-puller"
NAMESPACE="kserve-test"
KSA_NAME="vllm-serving-sa"

echo "=== GCP Infrastructure Setup ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo "Bucket:     gs://${BUCKET_NAME}"

# 1. Enable GCP Services
echo -e "\nEnabling required GCP Service APIs..."
gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    storage-component.googleapis.com \
    iam.googleapis.com

# 2. Create Storage Bucket for Model Registry
echo -e "\nCreating Google Cloud Storage bucket..."
if gcloud storage buckets describe gs://${BUCKET_NAME} &>/dev/null; then
    echo "Bucket gs://${BUCKET_NAME} already exists."
else
    gcloud storage buckets create gs://${BUCKET_NAME} \
        --location=${REGION} \
        --uniform-bucket-level-access
    echo "Bucket gs://${BUCKET_NAME} created successfully."
fi

# 3. Create Service Account for model downloads
echo -e "\nSetting up Google Service Account (GSA)..."
if gcloud iam service-accounts describe ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com &>/dev/null; then
    echo "Service Account ${SA_NAME} already exists."
else
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="GKE Model Puller Service Account"
fi

# Bind Storage Object Viewer permission to the GSA
echo "Assigning storage.objectViewer role to GSA..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# 4. Configure IAM Workload Identity Binding
# Workload Identity is the Google-recommended best practice for GKE authentication.
# It binds a Kubernetes Service Account (KSA) to a GCP Google Service Account (GSA).
echo -e "\nConfiguring Workload Identity binding..."
gcloud iam service-accounts add-iam-policy-binding ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"

# 5. Instructions for Uploading Models
echo -e "\n=============================================="
echo "=== Setup Complete! Next Steps ==="
echo "=============================================="
echo "1. To sync your local model-cache weights to GCP, run:"
echo "   gcloud storage rsync -r model-cache/ gs://${BUCKET_NAME}/model-cache/"
echo ""
echo "2. When deploying to GKE, create the Kubernetes Service Account in namespace '${NAMESPACE}':"
echo "   kubectl create serviceaccount ${KSA_NAME} -n ${NAMESPACE}"
echo ""
echo "3. Annotate the KSA to link it to the Google Service Account:"
echo "   kubectl annotate serviceaccount ${KSA_NAME} -n ${NAMESPACE} \\"
echo "     iam.gke.io/gcp-service-account=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "=============================================="
