# Development Environment Configuration

project_name = "medical-imaging-pipeline"
environment  = "dev"
aws_region   = "us-east-1"

# S3 Configuration
s3_bucket_lifecycle_days = 30  # Shorter lifecycle for dev

# Lambda Configuration
lambda_runtime     = "python3.12"
lambda_timeout     = 300
lambda_memory_size = 256  # Smaller memory for dev to save costs

# CloudWatch Configuration
log_retention_days = 7  # Shorter retention for dev

# Step Functions Configuration
state_machine_name = "dicom-processing-workflow-dev"

# Security
enable_s3_encryption = true
enable_lambda_vpc    = false

# Additional tags
additional_tags = {
  Environment = "Development"
  CostCenter  = "Medical Imaging - Dev"
}
