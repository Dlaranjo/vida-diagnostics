variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "state_machine_name" {
  description = "Name for the Step Functions state machine"
  type        = string
}

variable "definition_path" {
  description = "Path to the state machine definition JSON file"
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of the Step Functions execution role"
  type        = string
}

variable "ingestion_lambda_arn" {
  description = "ARN of the ingestion Lambda function"
  type        = string
}

variable "validation_lambda_arn" {
  description = "ARN of the validation Lambda function"
  type        = string
}

variable "deidentification_lambda_arn" {
  description = "ARN of the deidentification Lambda function"
  type        = string
}

variable "raw_bucket_name" {
  description = "Name of the raw DICOM files bucket"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "enable_eventbridge_trigger" {
  description = "Enable EventBridge rule to trigger Step Functions on S3 uploads"
  type        = bool
  default     = false
}

variable "eventbridge_role_arn" {
  description = "ARN of the EventBridge execution role (required if enable_eventbridge_trigger is true)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to Step Functions resources"
  type        = map(string)
  default     = {}
}
