# S3 Module - Main Configuration
# Creates S3 buckets for data storage, models, logs, and artifacts

locals {
  # Common tags for all S3 resources
  s3_tags = merge(var.tags, {
    Component = "s3"
    Module    = "s3"
  })

  # Bucket names with random suffix for uniqueness
  bucket_names = {
    data      = "${var.project_name}-${var.environment}-data-${var.random_suffix}"
    models    = "${var.project_name}-${var.environment}-models-${var.random_suffix}"
    logs      = "${var.project_name}-${var.environment}-logs-${var.random_suffix}"
    artifacts = "${var.project_name}-${var.environment}-artifacts-${var.random_suffix}"
  }
}

# ===========================
# Data Bucket
# ===========================

# S3 bucket for storing GTFS data and processed datasets
resource "aws_s3_bucket" "data" {
  bucket = local.bucket_names.data

  tags = merge(local.s3_tags, {
    Name    = local.bucket_names.data
    Purpose = "DataStorage"
    Type    = "Primary"
  })
}

# Data bucket versioning
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# Data bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  count  = var.enable_server_side_encryption ? 1 : 0
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Data bucket public access block
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Data bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  depends_on = [aws_s3_bucket_versioning.data]
  bucket     = aws_s3_bucket.data.id

  rule {
    id     = "data_lifecycle"
    status = "Enabled"

    # Transition to IA storage class
    dynamic "transition" {
      for_each = var.transition_to_ia_days > 0 ? [1] : []
      content {
        days          = var.transition_to_ia_days
        storage_class = "STANDARD_IA"
      }
    }

    # Transition to Glacier storage class
    dynamic "transition" {
      for_each = var.transition_to_glacier_days > 0 ? [1] : []
      content {
        days          = var.transition_to_glacier_days
        storage_class = "GLACIER"
      }
    }

    # Expire objects
    dynamic "expiration" {
      for_each = var.lifecycle_expiration_days > 0 ? [1] : []
      content {
        days = var.lifecycle_expiration_days
      }
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    # Clean up old versions
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ===========================
# Models Bucket
# ===========================

# S3 bucket for storing ML models and artifacts
resource "aws_s3_bucket" "models" {
  bucket = local.bucket_names.models

  tags = merge(local.s3_tags, {
    Name    = local.bucket_names.models
    Purpose = "ModelStorage"
    Type    = "MLFlow"
  })
}

# Models bucket versioning
resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# Models bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  count  = var.enable_server_side_encryption ? 1 : 0
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Models bucket public access block
resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Models bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "models" {
  depends_on = [aws_s3_bucket_versioning.models]
  bucket     = aws_s3_bucket.models.id

  rule {
    id     = "models_lifecycle"
    status = "Enabled"

    # Keep current versions longer for models
    dynamic "transition" {
      for_each = var.transition_to_ia_days > 0 ? [1] : []
      content {
        days          = var.transition_to_ia_days * 2 # Keep models in standard longer
        storage_class = "STANDARD_IA"
      }
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    # Keep old model versions for longer
    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }
}

# ===========================
# Logs Bucket
# ===========================

# S3 bucket for storing application and system logs
resource "aws_s3_bucket" "logs" {
  bucket = local.bucket_names.logs

  tags = merge(local.s3_tags, {
    Name    = local.bucket_names.logs
    Purpose = "LogStorage"
    Type    = "Operational"
  })
}

# Logs bucket versioning
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Disabled" # Don't version logs to save space
  }
}

# Logs bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  count  = var.enable_server_side_encryption ? 1 : 0
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Logs bucket public access block
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Logs bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "logs_lifecycle"
    status = "Enabled"

    # Transition logs to IA quickly
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier for long-term archival
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Delete old logs
    expiration {
      days = var.lifecycle_expiration_days > 0 ? var.lifecycle_expiration_days : 365
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# ===========================
# Artifacts Bucket
# ===========================

# S3 bucket for storing deployment artifacts and backups
resource "aws_s3_bucket" "artifacts" {
  bucket = local.bucket_names.artifacts

  tags = merge(local.s3_tags, {
    Name    = local.bucket_names.artifacts
    Purpose = "ArtifactStorage"
    Type    = "Deployment"
  })
}

# Artifacts bucket versioning
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# Artifacts bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  count  = var.enable_server_side_encryption ? 1 : 0
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Artifacts bucket public access block
resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ===========================
# Cross-Region Replication (Optional)
# ===========================

# Replication configuration for data bucket
resource "aws_s3_bucket_replication_configuration" "data" {
  count = var.enable_cross_region_replication ? 1 : 0

  role   = aws_iam_role.replication[0].arn
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "data_replication"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.data_replica[0].arn
      storage_class = "STANDARD_IA"
    }
  }

  depends_on = [aws_s3_bucket_versioning.data]
}

# Replica bucket for cross-region replication
resource "aws_s3_bucket" "data_replica" {
  count = var.enable_cross_region_replication ? 1 : 0

  provider = aws.replica
  bucket   = "${local.bucket_names.data}-replica"

  tags = merge(local.s3_tags, {
    Name    = "${local.bucket_names.data}-replica"
    Purpose = "DataReplication"
    Type    = "Replica"
  })
}

# Replica bucket versioning
resource "aws_s3_bucket_versioning" "data_replica" {
  count = var.enable_cross_region_replication ? 1 : 0

  provider = aws.replica
  bucket   = aws_s3_bucket.data_replica[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# IAM role for replication
resource "aws_iam_role" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-s3-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })

  tags = local.s3_tags
}

# IAM policy for replication
resource "aws_iam_role_policy" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-s3-replication-policy"
  role = aws_iam_role.replication[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.data.arn}/*"
        ]
      },
      {
        Action = [
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.data.arn
        ]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.data_replica[0].arn}/*"
        ]
      }
    ]
  })
}

# ===========================
# S3 Bucket Notifications (Optional)
# ===========================

# SNS topic for S3 notifications
resource "aws_sns_topic" "s3_notifications" {
  count = var.enable_s3_notifications ? 1 : 0

  name = "${var.project_name}-${var.environment}-s3-notifications"

  tags = local.s3_tags
}

# S3 bucket notification for data bucket
resource "aws_s3_bucket_notification" "data" {
  count  = var.enable_s3_notifications ? 1 : 0
  bucket = aws_s3_bucket.data.id

  topic {
    topic_arn     = aws_sns_topic.s3_notifications[0].arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "gtfs/"
    filter_suffix = ".txt"
  }

  depends_on = [aws_sns_topic_policy.s3_notifications]
}

# SNS topic policy for S3 notifications
resource "aws_sns_topic_policy" "s3_notifications" {
  count = var.enable_s3_notifications ? 1 : 0

  arn = aws_sns_topic.s3_notifications[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.s3_notifications[0].arn
        Condition = {
          StringEquals = {
            "aws:SourceArn" = aws_s3_bucket.data.arn
          }
        }
      }
    ]
  })
}
