output "raw_bucket_id" {
  description = "ID of the raw DICOM files bucket"
  value       = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  description = "ARN of the raw DICOM files bucket"
  value       = aws_s3_bucket.raw.arn
}

output "processed_bucket_id" {
  description = "ID of the processed DICOM files bucket"
  value       = aws_s3_bucket.processed.id
}

output "processed_bucket_arn" {
  description = "ARN of the processed DICOM files bucket"
  value       = aws_s3_bucket.processed.arn
}

output "logs_bucket_id" {
  description = "ID of the logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN of the logs bucket"
  value       = aws_s3_bucket.logs.arn
}
