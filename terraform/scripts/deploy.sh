#!/bin/bash
# Script to deploy Medical Imaging Pipeline infrastructure with Terraform

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if environment is valid
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi

print_info "Deploying Medical Imaging Pipeline to $ENVIRONMENT environment..."

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Step 1: Build Lambda layer
print_info "Step 1: Building Lambda layer..."
if [ -f "$SCRIPT_DIR/build_lambda_layer.sh" ]; then
    bash "$SCRIPT_DIR/build_lambda_layer.sh"
else
    print_error "build_lambda_layer.sh not found"
    exit 1
fi

# Step 2: Initialize Terraform
print_info "Step 2: Initializing Terraform..."
terraform init

# Step 3: Select or create workspace
print_info "Step 3: Selecting workspace: $ENVIRONMENT..."
terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"

# Step 4: Validate Terraform configuration
print_info "Step 4: Validating Terraform configuration..."
terraform validate

# Step 5: Format check
print_info "Step 5: Checking Terraform formatting..."
terraform fmt -check || {
    print_warning "Terraform files are not properly formatted. Running fmt..."
    terraform fmt -recursive
}

# Step 6: Plan
print_info "Step 6: Creating Terraform plan..."
TFVARS_FILE="environments/$ENVIRONMENT/terraform.tfvars"
if [ -f "$TFVARS_FILE" ]; then
    terraform plan -var-file="$TFVARS_FILE" -out=tfplan
else
    print_error "Variables file not found: $TFVARS_FILE"
    exit 1
fi

# Step 7: Ask for confirmation
print_warning "Review the plan above. Do you want to apply these changes? (yes/no)"
read -r CONFIRMATION

if [ "$CONFIRMATION" != "yes" ]; then
    print_info "Deployment cancelled by user"
    rm -f tfplan
    exit 0
fi

# Step 8: Apply
print_info "Step 7: Applying Terraform configuration..."
terraform apply tfplan

# Cleanup
rm -f tfplan

# Step 9: Show outputs
print_info "Step 8: Deployment completed! Here are the outputs:"
echo ""
terraform output -json | jq '.'

print_info "Deployment Summary:"
terraform output deployment_summary

print_info "To test the deployment:"
echo "  1. Upload a DICOM file to the raw bucket:"
echo "     aws s3 cp test.dcm s3://\$(terraform output -raw raw_bucket_name)/"
echo ""
echo "  2. Check Step Functions execution:"
echo "     aws stepfunctions list-executions --state-machine-arn \$(terraform output -raw state_machine_arn)"
echo ""
echo "  3. View Lambda logs:"
echo "     aws logs tail /aws/lambda/\$(terraform output -raw ingestion_function_name) --follow"

print_info "Done!"
