# Main Terraform Outputs

# S3 Buckets
output "raw_bucket_name" {
  description = "Name of the raw DICOM files bucket"
  value       = module.s3.raw_bucket_id
}

output "raw_bucket_arn" {
  description = "ARN of the raw DICOM files bucket"
  value       = module.s3.raw_bucket_arn
}

output "processed_bucket_name" {
  description = "Name of the processed DICOM files bucket"
  value       = module.s3.processed_bucket_id
}

output "processed_bucket_arn" {
  description = "ARN of the processed DICOM files bucket"
  value       = module.s3.processed_bucket_arn
}

output "logs_bucket_name" {
  description = "Name of the logs bucket"
  value       = module.s3.logs_bucket_id
}

# Lambda Functions
output "ingestion_function_name" {
  description = "Name of the ingestion Lambda function"
  value       = module.lambda.ingestion_function_name
}

output "ingestion_function_arn" {
  description = "ARN of the ingestion Lambda function"
  value       = module.lambda.ingestion_function_arn
}

output "validation_function_name" {
  description = "Name of the validation Lambda function"
  value       = module.lambda.validation_function_name
}

output "validation_function_arn" {
  description = "ARN of the validation Lambda function"
  value       = module.lambda.validation_function_arn
}

output "deidentification_function_name" {
  description = "Name of the deidentification Lambda function"
  value       = module.lambda.deidentification_function_name
}

output "deidentification_function_arn" {
  description = "ARN of the deidentification Lambda function"
  value       = module.lambda.deidentification_function_arn
}

# IAM Roles
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = module.iam.lambda_execution_role_arn
}

output "step_functions_execution_role_arn" {
  description = "ARN of the Step Functions execution role"
  value       = module.iam.step_functions_execution_role_arn
}

# Step Functions
output "state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = module.step_functions.state_machine_name
}

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.step_functions.state_machine_arn
}

# Summary
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    environment          = var.environment
    region               = var.aws_region
    raw_bucket           = module.s3.raw_bucket_id
    processed_bucket     = module.s3.processed_bucket_id
    ingestion_lambda     = module.lambda.ingestion_function_name
    validation_lambda    = module.lambda.validation_function_name
    deidentification_lambda = module.lambda.deidentification_function_name
    state_machine        = module.step_functions.state_machine_name
  }
}
