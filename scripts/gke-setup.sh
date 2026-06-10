#!/usr/bin/env bash
# gke-cluster-setup.sh
# Provisions a GKE Autopilot cluster optimized for serving LLMs on GPUs.

set -eo pipefail

PROJECT_ID=$(gcloud config get-value project)
CLUSTER_NAME="ml-serving-cluster"
REGION="us-central1" # Or us-central1 depending on where your GPU quota is

echo "=== GKE Autopilot Cluster Provisioning ==="
echo "Project ID:   ${PROJECT_ID}"
echo "Cluster Name: ${CLUSTER_NAME}"
echo "Region:       ${REGION}"
echo "-----------------------------------------"

# 1. Create the GKE Autopilot Cluster
# Autopilot is recommended for dev/test as it automatically provisions nodes
# and installs NVIDIA GPU drivers when a GPU workload is requested.
echo "Creating GKE Autopilot cluster... This can take 5-10 minutes."
gcloud container clusters create-auto ${CLUSTER_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID}

# 2. Get Credentials (configure kubectl)
echo -e "\nConfiguring kubectl to connect to the new cluster..."
gcloud container clusters get-credentials ${CLUSTER_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID}

echo -e "\n=== GKE Cluster Ready! ==="
echo "You can check cluster access by running: kubectl get nodes"
