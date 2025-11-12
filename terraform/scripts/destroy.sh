#!/bin/bash
# Script to destroy Medical Imaging Pipeline infrastructure

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

print_warning "You are about to DESTROY all infrastructure in $ENVIRONMENT environment!"
print_warning "This action cannot be undone."
echo ""
print_warning "Type 'destroy-$ENVIRONMENT' to confirm:"
read -r CONFIRMATION

if [ "$CONFIRMATION" != "destroy-$ENVIRONMENT" ]; then
    print_info "Destruction cancelled by user"
    exit 0
fi

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Select workspace
print_info "Selecting workspace: $ENVIRONMENT..."
terraform workspace select "$ENVIRONMENT" 2>/dev/null || {
    print_error "Workspace $ENVIRONMENT does not exist"
    exit 1
}

# Get bucket names before destroying
print_info "Getting S3 bucket names..."
RAW_BUCKET=$(terraform output -raw raw_bucket_name 2>/dev/null || echo "")
PROCESSED_BUCKET=$(terraform output -raw processed_bucket_name 2>/dev/null || echo "")
LOGS_BUCKET=$(terraform output -raw logs_bucket_name 2>/dev/null || echo "")

# Empty S3 buckets (Terraform cannot destroy non-empty buckets)
if [ -n "$RAW_BUCKET" ]; then
    print_info "Emptying raw bucket: $RAW_BUCKET..."
    aws s3 rm "s3://$RAW_BUCKET" --recursive 2>/dev/null || true
fi

if [ -n "$PROCESSED_BUCKET" ]; then
    print_info "Emptying processed bucket: $PROCESSED_BUCKET..."
    aws s3 rm "s3://$PROCESSED_BUCKET" --recursive 2>/dev/null || true
fi

if [ -n "$LOGS_BUCKET" ]; then
    print_info "Emptying logs bucket: $LOGS_BUCKET..."
    aws s3 rm "s3://$LOGS_BUCKET" --recursive 2>/dev/null || true
fi

# Destroy infrastructure
print_info "Destroying Terraform infrastructure..."
TFVARS_FILE="environments/$ENVIRONMENT/terraform.tfvars"
if [ -f "$TFVARS_FILE" ]; then
    terraform destroy -var-file="$TFVARS_FILE" -auto-approve
else
    print_error "Variables file not found: $TFVARS_FILE"
    exit 1
fi

print_info "Infrastructure destroyed successfully!"
print_info "Note: The following may still exist and require manual cleanup:"
echo "  - Terraform state in S3 (if using remote backend)"
echo "  - DynamoDB state lock table"
echo "  - CloudWatch Log Groups (if retain_logs was enabled)"

print_warning "To completely remove all traces:"
echo "  1. Delete Terraform state bucket:"
echo "     aws s3 rb s3://medical-imaging-terraform-state --force"
echo ""
echo "  2. Delete DynamoDB lock table:"
echo "     aws dynamodb delete-table --table-name medical-imaging-terraform-locks"
echo ""
echo "  3. Delete CloudWatch log groups:"
echo "     aws logs delete-log-group --log-group-name /aws/lambda/medical-imaging-pipeline-*"
echo "     aws logs delete-log-group --log-group-name /aws/stepfunctions/*"

print_info "Done!"
