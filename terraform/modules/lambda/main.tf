# Lambda Module - Creates Lambda functions for DICOM processing

# Data source to create Lambda deployment package
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = var.source_path
  output_path = "${path.module}/lambda_package.zip"
}

# Lambda Layer for dependencies (pydicom, boto3, etc.)
resource "aws_lambda_layer_version" "dependencies" {
  filename            = var.dependencies_package_path
  layer_name          = "${var.project_name}-dependencies"
  compatible_runtimes = [var.runtime]
  description         = "Python dependencies for DICOM processing"

  lifecycle {
    create_before_destroy = true
  }
}

# Ingestion Lambda Function
resource "aws_lambda_function" "ingestion" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-ingestion"
  role             = var.execution_role_arn
  handler          = "lambda_functions.ingestion_handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      RAW_BUCKET       = var.raw_bucket_name
      PROCESSED_BUCKET = var.processed_bucket_name
      ENVIRONMENT      = var.environment
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-ingestion"
      Type = "Ingestion Function"
    }
  )
}

# CloudWatch Log Group for Ingestion
resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${aws_lambda_function.ingestion.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Validation Lambda Function
resource "aws_lambda_function" "validation" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-validation"
  role             = var.execution_role_arn
  handler          = "lambda_functions.validation_handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      RAW_BUCKET       = var.raw_bucket_name
      PROCESSED_BUCKET = var.processed_bucket_name
      ENVIRONMENT      = var.environment
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-validation"
      Type = "Validation Function"
    }
  )
}

# CloudWatch Log Group for Validation
resource "aws_cloudwatch_log_group" "validation" {
  name              = "/aws/lambda/${aws_lambda_function.validation.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Deidentification Lambda Function
resource "aws_lambda_function" "deidentification" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-deidentification"
  role             = var.execution_role_arn
  handler          = "lambda_functions.deidentification_handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      RAW_BUCKET       = var.raw_bucket_name
      PROCESSED_BUCKET = var.processed_bucket_name
      ENVIRONMENT      = var.environment
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-deidentification"
      Type = "Deidentification Function"
    }
  )
}

# CloudWatch Log Group for Deidentification
resource "aws_cloudwatch_log_group" "deidentification" {
  name              = "/aws/lambda/${aws_lambda_function.deidentification.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# S3 trigger for Ingestion Lambda (when files are uploaded to raw bucket)
resource "aws_lambda_permission" "allow_s3_ingestion" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.raw_bucket_arn
}

resource "aws_s3_bucket_notification" "raw_bucket_notification" {
  bucket = var.raw_bucket_id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingestion.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".dcm"
  }

  depends_on = [aws_lambda_permission.allow_s3_ingestion]
}
