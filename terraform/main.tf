# Main Terraform configuration for Medical Imaging Pipeline

locals {
  # Generate unique bucket names with project name and environment
  raw_bucket_name = var.raw_bucket_name != "" ? var.raw_bucket_name : "${var.project_name}-${var.environment}-raw-dicom"
  processed_bucket_name = var.processed_bucket_name != "" ? var.processed_bucket_name : "${var.project_name}-${var.environment}-processed-dicom"
  logs_bucket_name      = var.logs_bucket_name != "" ? var.logs_bucket_name : "${var.project_name}-${var.environment}-logs"

  # Common tags
  common_tags = merge(
    var.additional_tags,
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# S3 Buckets Module
module "s3" {
  source = "./modules/s3"

  project_name          = var.project_name
  raw_bucket_name       = local.raw_bucket_name
  processed_bucket_name = local.processed_bucket_name
  logs_bucket_name      = local.logs_bucket_name
  enable_encryption     = var.enable_s3_encryption
  lifecycle_days        = var.s3_bucket_lifecycle_days

  tags = local.common_tags
}

# Lambda Functions Module
module "lambda" {
  source = "./modules/lambda"

  project_name              = var.project_name
  environment               = var.environment
  source_path               = var.lambda_source_path
  dependencies_package_path = "${path.module}/lambda_layer.zip"
  execution_role_arn        = module.iam.lambda_execution_role_arn
  raw_bucket_name           = module.s3.raw_bucket_id
  raw_bucket_id             = module.s3.raw_bucket_id
  raw_bucket_arn            = module.s3.raw_bucket_arn
  processed_bucket_name     = module.s3.processed_bucket_id
  runtime                   = var.lambda_runtime
  timeout                   = var.lambda_timeout
  memory_size               = var.lambda_memory_size
  log_retention_days        = var.log_retention_days
  enable_vpc                = var.enable_lambda_vpc
  subnet_ids                = var.subnet_ids
  security_group_ids        = []

  tags = local.common_tags

  depends_on = [module.s3, module.iam]
}

# IAM Roles and Policies Module
module "iam" {
  source = "./modules/iam"

  project_name          = var.project_name
  raw_bucket_arn        = module.s3.raw_bucket_arn
  processed_bucket_arn  = module.s3.processed_bucket_arn
  enable_lambda_vpc     = var.enable_lambda_vpc

  tags = local.common_tags

  depends_on = [module.s3]
}

# Step Functions State Machine Module
module "step_functions" {
  source = "./modules/step_functions"

  project_name                 = var.project_name
  state_machine_name           = var.state_machine_name
  definition_path              = var.state_machine_definition_path
  execution_role_arn           = module.iam.step_functions_execution_role_arn
  ingestion_lambda_arn         = module.lambda.ingestion_function_arn
  validation_lambda_arn        = module.lambda.validation_function_arn
  deidentification_lambda_arn  = module.lambda.deidentification_function_arn
  raw_bucket_name              = module.s3.raw_bucket_id
  log_retention_days           = var.log_retention_days
  enable_eventbridge_trigger   = false

  tags = local.common_tags

  depends_on = [module.lambda, module.iam]
}
