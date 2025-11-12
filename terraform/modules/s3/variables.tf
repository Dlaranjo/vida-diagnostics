variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "raw_bucket_name" {
  description = "Name for raw DICOM files bucket"
  type        = string
}

variable "processed_bucket_name" {
  description = "Name for processed DICOM files bucket"
  type        = string
}

variable "logs_bucket_name" {
  description = "Name for logs bucket"
  type        = string
}

variable "enable_encryption" {
  description = "Enable S3 bucket encryption"
  type        = bool
  default     = true
}

variable "lifecycle_days" {
  description = "Days before transitioning to cheaper storage"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Tags to apply to S3 resources"
  type        = map(string)
  default     = {}
}
