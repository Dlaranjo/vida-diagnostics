# Terraform backend configuration for remote state
# Note: Backend cannot use variables, so you need to configure this manually
# or use terraform init -backend-config flags

terraform {
  # backend "s3" {
  #   # bucket         = "medical-imaging-terraform-state"
  #   # key            = "terraform.tfstate"
  #   # region         = "us-east-1"
  #   # dynamodb_table = "medical-imaging-terraform-locks"
  #   # encrypt        = true
  #
  #   # Uncomment and configure the above values before running terraform init
  #   # Or use: terraform init -backend-config="bucket=your-bucket-name"
  # }
}

# To set up the backend infrastructure, run these AWS CLI commands first:
#
# 1. Create S3 bucket for state:
#    aws s3 mb s3://medical-imaging-terraform-state --region us-east-1
#    aws s3api put-bucket-versioning --bucket medical-imaging-terraform-state \
#      --versioning-configuration Status=Enabled
#    aws s3api put-bucket-encryption --bucket medical-imaging-terraform-state \
#      --server-side-encryption-configuration \
#      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#
# 2. Create DynamoDB table for locking:
#    aws dynamodb create-table --table-name medical-imaging-terraform-locks \
#      --attribute-definitions AttributeName=LockID,AttributeType=S \
#      --key-schema AttributeName=LockID,KeyType=HASH \
#      --billing-mode PAY_PER_REQUEST --region us-east-1
