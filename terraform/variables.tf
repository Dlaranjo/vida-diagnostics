# General Configuration
variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "medical-imaging-pipeline"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

# S3 Configuration
variable "raw_bucket_name" {
  description = "S3 bucket name for raw DICOM files"
  type        = string
  default     = ""
}

variable "processed_bucket_name" {
  description = "S3 bucket name for processed/deidentified DICOM files"
  type        = string
  default     = ""
}

variable "logs_bucket_name" {
  description = "S3 bucket name for access logs"
  type        = string
  default     = ""
}

variable "s3_bucket_lifecycle_days" {
  description = "Number of days before transitioning objects to cheaper storage"
  type        = number
  default     = 90
}

# Lambda Configuration
variable "lambda_runtime" {
  description = "Python runtime version for Lambda functions"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_source_path" {
  description = "Path to Lambda function source code"
  type        = string
  default     = "../medical-imaging-pipeline/src"
}

variable "lambda_requirements_path" {
  description = "Path to Lambda requirements.txt"
  type        = string
  default     = "../medical-imaging-pipeline/requirements.txt"
}

# Step Functions Configuration
variable "state_machine_name" {
  description = "Name for the Step Functions state machine"
  type        = string
  default     = "dicom-processing-workflow"
}

variable "state_machine_definition_path" {
  description = "Path to Step Functions state machine definition"
  type        = string
  default     = "../medical-imaging-pipeline/state_machines/dicom_processing_workflow.json"
}

# CloudWatch Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Security
variable "enable_s3_encryption" {
  description = "Enable S3 bucket encryption"
  type        = bool
  default     = true
}

variable "enable_lambda_vpc" {
  description = "Enable Lambda VPC configuration"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC ID for Lambda functions (if enable_lambda_vpc is true)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for Lambda functions (if enable_lambda_vpc is true)"
  type        = list(string)
  default     = []
}
