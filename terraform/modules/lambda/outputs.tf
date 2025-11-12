output "ingestion_function_arn" {
  description = "ARN of the ingestion Lambda function"
  value       = aws_lambda_function.ingestion.arn
}

output "ingestion_function_name" {
  description = "Name of the ingestion Lambda function"
  value       = aws_lambda_function.ingestion.function_name
}

output "validation_function_arn" {
  description = "ARN of the validation Lambda function"
  value       = aws_lambda_function.validation.arn
}

output "validation_function_name" {
  description = "Name of the validation Lambda function"
  value       = aws_lambda_function.validation.function_name
}

output "deidentification_function_arn" {
  description = "ARN of the deidentification Lambda function"
  value       = aws_lambda_function.deidentification.arn
}

output "deidentification_function_name" {
  description = "Name of the deidentification Lambda function"
  value       = aws_lambda_function.deidentification.function_name
}

output "lambda_function_arns" {
  description = "List of all Lambda function ARNs"
  value = [
    aws_lambda_function.ingestion.arn,
    aws_lambda_function.validation.arn,
    aws_lambda_function.deidentification.arn
  ]
}
