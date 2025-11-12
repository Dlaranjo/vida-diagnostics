# Production Environment Configuration

project_name = "medical-imaging-pipeline"
environment  = "prod"
aws_region   = "us-east-1"

# S3 Configuration
s3_bucket_lifecycle_days = 90  # Longer lifecycle for prod

# Lambda Configuration
lambda_runtime     = "python3.12"
lambda_timeout     = 300
lambda_memory_size = 512  # More memory for production performance

# CloudWatch Configuration
log_retention_days = 30  # Longer retention for prod compliance

# Step Functions Configuration
state_machine_name = "dicom-processing-workflow-prod"

# Security
enable_s3_encryption = true
enable_lambda_vpc    = false  # Set to true if using VPC

# Optional: VPC configuration for production
# enable_lambda_vpc = true
# vpc_id     = "vpc-xxxxxxxxxxxxx"
# subnet_ids = ["subnet-xxxxxxxxxxxxx", "subnet-yyyyyyyyyyyyy"]

# Additional tags
additional_tags = {
  Environment = "Production"
  CostCenter  = "Medical Imaging - Prod"
  Compliance  = "HIPAA"
}
