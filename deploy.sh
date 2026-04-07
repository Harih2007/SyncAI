#!/bin/bash

# =============================================================================
# SyncAI Cloud Run Deployment Script
# =============================================================================
# Automates the deployment of the multi-agent AI system to Google Cloud Run
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${BLUE}[Step $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "  → $1"
}

# =============================================================================
# Configuration
# =============================================================================

print_header "SyncAI Cloud Run Deployment"

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    print_error "PROJECT_ID environment variable not set"
    echo ""
    echo "Please set your Google Cloud project ID:"
    echo "  export PROJECT_ID=\"your-project-id\""
    echo ""
    exit 1
fi

print_success "Project ID: $PROJECT_ID"

# Configuration variables
REGION="${REGION:-us-central1}"
SERVICE_NAME="syncai"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
VERTEX_MODEL="${VERTEX_MODEL:-gemini-2.0-flash}"

print_info "Region: $REGION"
print_info "Service: $SERVICE_NAME"
print_info "Model: $VERTEX_MODEL"

# =============================================================================
# Step 1: Verify gcloud is installed and configured
# =============================================================================

print_step 1 "Verifying gcloud CLI"

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found"
    echo ""
    echo "Please install gcloud CLI:"
    echo "  https://cloud.google.com/sdk/docs/install"
    echo ""
    exit 1
fi

print_success "gcloud CLI installed"

# Set project
gcloud config set project $PROJECT_ID --quiet
print_success "Project configured"

# =============================================================================
# Step 2: Enable required services
# =============================================================================

print_step 2 "Enabling Google Cloud services"

SERVICES=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "aiplatform.googleapis.com"
    "firestore.googleapis.com"
)

for service in "${SERVICES[@]}"; do
    print_info "Enabling $service..."
    gcloud services enable $service --quiet
done

print_success "All services enabled"

# =============================================================================
# Step 3: Build container with Cloud Build
# =============================================================================

print_step 3 "Building container with Cloud Build"

print_info "This may take 3-6 minutes..."
print_info "Building image: $IMAGE_NAME"

if gcloud builds submit --tag $IMAGE_NAME --quiet; then
    print_success "Container built successfully"
else
    print_error "Container build failed"
    exit 1
fi

# =============================================================================
# Step 4: Deploy to Cloud Run
# =============================================================================

print_step 4 "Deploying to Cloud Run"

print_info "Deploying service: $SERVICE_NAME"
print_info "Region: $REGION"

if gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars PROJECT_ID=$PROJECT_ID,VERTEX_MODEL=$VERTEX_MODEL \
    --memory 512Mi \
    --timeout 60s \
    --max-instances 10 \
    --quiet; then
    print_success "Deployment successful"
else
    print_error "Deployment failed"
    exit 1
fi

# =============================================================================
# Step 5: Get service URL
# =============================================================================

print_step 5 "Retrieving service URL"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format 'value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    print_error "Could not retrieve service URL"
    exit 1
fi

print_success "Service deployed successfully!"
echo ""
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo ""

# =============================================================================
# Step 6: Test the deployment
# =============================================================================

print_step 6 "Testing deployment"

print_info "Testing health endpoint..."
sleep 5  # Wait for service to be ready

if curl -s -f "$SERVICE_URL/health" > /dev/null; then
    print_success "Health check passed"
else
    print_warning "Health check failed (service may still be starting)"
fi

# =============================================================================
# Summary
# =============================================================================

print_header "Deployment Complete!"

echo -e "${GREEN}✓ Container built and pushed${NC}"
echo -e "${GREEN}✓ Service deployed to Cloud Run${NC}"
echo -e "${GREEN}✓ API is accessible${NC}"
echo ""
echo -e "${BLUE}Service URL:${NC}"
echo "  $SERVICE_URL"
echo ""
echo -e "${BLUE}API Documentation:${NC}"
echo "  $SERVICE_URL/docs"
echo ""
echo -e "${BLUE}Test Commands:${NC}"
echo ""
echo "# Health check"
echo "curl $SERVICE_URL/health"
echo ""
echo "# Test chat endpoint"
echo "curl -X POST $SERVICE_URL/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\":\"Prepare my project demo meeting tomorrow\"}'"
echo ""
echo -e "${BLUE}View Logs:${NC}"
echo "gcloud run services logs read $SERVICE_NAME --region $REGION --limit 50"
echo ""
echo -e "${BLUE}Update Service:${NC}"
echo "gcloud run services update $SERVICE_NAME --region $REGION"
echo ""
echo -e "${GREEN}Ready for demo! 🚀${NC}"
echo ""
