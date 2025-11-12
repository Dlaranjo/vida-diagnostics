variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "source_path" {
  description = "Path to Lambda function source code"
  type        = string
}

variable "dependencies_package_path" {
  description = "Path to Lambda dependencies package (zip)"
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of the Lambda execution role"
  type        = string
}

variable "raw_bucket_name" {
  description = "Name of the raw DICOM files bucket"
  type        = string
}

variable "raw_bucket_id" {
  description = "ID of the raw DICOM files bucket"
  type        = string
}

variable "raw_bucket_arn" {
  description = "ARN of the raw DICOM files bucket"
  type        = string
}

variable "processed_bucket_name" {
  description = "Name of the processed DICOM files bucket"
  type        = string
}

variable "runtime" {
  description = "Python runtime version"
  type        = string
  default     = "python3.12"
}

variable "timeout" {
  description = "Function timeout in seconds"
  type        = number
  default     = 300
}

variable "memory_size" {
  description = "Function memory size in MB"
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "enable_vpc" {
  description = "Enable VPC configuration"
  type        = bool
  default     = false
}

variable "subnet_ids" {
  description = "Subnet IDs for VPC configuration"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for VPC configuration"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to Lambda resources"
  type        = map(string)
  default     = {}
}
