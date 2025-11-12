variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "raw_bucket_arn" {
  description = "ARN of the raw DICOM files bucket"
  type        = string
}

variable "processed_bucket_arn" {
  description = "ARN of the processed DICOM files bucket"
  type        = string
}

variable "enable_lambda_vpc" {
  description = "Enable Lambda VPC configuration"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to IAM resources"
  type        = map(string)
  default     = {}
}
