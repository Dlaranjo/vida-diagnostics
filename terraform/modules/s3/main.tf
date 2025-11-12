# S3 Module - Creates buckets for DICOM pipeline

# Raw DICOM files bucket (input)
resource "aws_s3_bucket" "raw" {
  bucket = var.raw_bucket_name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-raw"
      Type = "Raw DICOM Storage"
    }
  )
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  count  = var.enable_encryption ? 1 : 0
  bucket = aws_s3_bucket.raw.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket = aws_s3_bucket.raw.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = var.lifecycle_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_days * 2
      storage_class = "GLACIER"
    }
  }
}

# Processed/deidentified DICOM files bucket (output)
resource "aws_s3_bucket" "processed" {
  bucket = var.processed_bucket_name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-processed"
      Type = "Processed DICOM Storage"
    }
  )
}

resource "aws_s3_bucket_versioning" "processed" {
  bucket = aws_s3_bucket.processed.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed" {
  count  = var.enable_encryption ? 1 : 0
  bucket = aws_s3_bucket.processed.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "processed" {
  bucket = aws_s3_bucket.processed.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "processed" {
  bucket = aws_s3_bucket.processed.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = var.lifecycle_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_days * 2
      storage_class = "GLACIER"
    }
  }
}

# Logs bucket
resource "aws_s3_bucket" "logs" {
  bucket = var.logs_bucket_name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-logs"
      Type = "Access Logs"
    }
  )
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  count  = var.enable_encryption ? 1 : 0
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

# Enable logging for raw bucket
resource "aws_s3_bucket_logging" "raw" {
  bucket = aws_s3_bucket.raw.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "raw-bucket-logs/"
}

# Enable logging for processed bucket
resource "aws_s3_bucket_logging" "processed" {
  bucket = aws_s3_bucket.processed.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "processed-bucket-logs/"
}
