# S3 Module Outputs
# This file defines all output values from the S3 module

# ===========================
# Data Bucket Outputs
# ===========================

output "data_bucket_id" {
  description = "ID of the data bucket"
  value       = aws_s3_bucket.data.id
}

output "data_bucket_name" {
  description = "Name of the data bucket"
  value       = aws_s3_bucket.data.bucket
}

output "data_bucket_arn" {
  description = "ARN of the data bucket"
  value       = aws_s3_bucket.data.arn
}

output "data_bucket_domain_name" {
  description = "Domain name of the data bucket"
  value       = aws_s3_bucket.data.bucket_domain_name
}

output "data_bucket_hosted_zone_id" {
  description = "Hosted zone ID of the data bucket"
  value       = aws_s3_bucket.data.hosted_zone_id
}

output "data_bucket_region" {
  description = "Region of the data bucket"
  value       = aws_s3_bucket.data.region
}

# ===========================
# Models Bucket Outputs
# ===========================

output "models_bucket_id" {
  description = "ID of the models bucket"
  value       = aws_s3_bucket.models.id
}

output "models_bucket_name" {
  description = "Name of the models bucket"
  value       = aws_s3_bucket.models.bucket
}

output "models_bucket_arn" {
  description = "ARN of the models bucket"
  value       = aws_s3_bucket.models.arn
}

output "models_bucket_domain_name" {
  description = "Domain name of the models bucket"
  value       = aws_s3_bucket.models.bucket_domain_name
}

output "models_bucket_hosted_zone_id" {
  description = "Hosted zone ID of the models bucket"
  value       = aws_s3_bucket.models.hosted_zone_id
}

output "models_bucket_region" {
  description = "Region of the models bucket"
  value       = aws_s3_bucket.models.region
}

# ===========================
# Logs Bucket Outputs
# ===========================

output "logs_bucket_id" {
  description = "ID of the logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_name" {
  description = "Name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket
}

output "logs_bucket_arn" {
  description = "ARN of the logs bucket"
  value       = aws_s3_bucket.logs.arn
}

output "logs_bucket_domain_name" {
  description = "Domain name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket_domain_name
}

output "logs_bucket_hosted_zone_id" {
  description = "Hosted zone ID of the logs bucket"
  value       = aws_s3_bucket.logs.hosted_zone_id
}

output "logs_bucket_region" {
  description = "Region of the logs bucket"
  value       = aws_s3_bucket.logs.region
}

# ===========================
# Artifacts Bucket Outputs
# ===========================

output "artifacts_bucket_id" {
  description = "ID of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_name" {
  description = "Name of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.bucket
}

output "artifacts_bucket_arn" {
  description = "ARN of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.arn
}

output "artifacts_bucket_domain_name" {
  description = "Domain name of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.bucket_domain_name
}

output "artifacts_bucket_hosted_zone_id" {
  description = "Hosted zone ID of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.hosted_zone_id
}

output "artifacts_bucket_region" {
  description = "Region of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.region
}

# ===========================
# Replication Outputs
# ===========================

output "data_replica_bucket_id" {
  description = "ID of the data replica bucket"
  value       = var.enable_cross_region_replication ? aws_s3_bucket.data_replica[0].id : null
}

output "data_replica_bucket_name" {
  description = "Name of the data replica bucket"
  value       = var.enable_cross_region_replication ? aws_s3_bucket.data_replica[0].bucket : null
}

output "data_replica_bucket_arn" {
  description = "ARN of the data replica bucket"
  value       = var.enable_cross_region_replication ? aws_s3_bucket.data_replica[0].arn : null
}

output "replication_role_arn" {
  description = "ARN of the replication IAM role"
  value       = var.enable_cross_region_replication ? aws_iam_role.replication[0].arn : null
}

# ===========================
# Notification Outputs
# ===========================

output "s3_notifications_topic_arn" {
  description = "ARN of the SNS topic for S3 notifications"
  value       = var.enable_s3_notifications ? aws_sns_topic.s3_notifications[0].arn : null
}

output "s3_notifications_topic_name" {
  description = "Name of the SNS topic for S3 notifications"
  value       = var.enable_s3_notifications ? aws_sns_topic.s3_notifications[0].name : null
}

# ===========================
# All Bucket Names (for convenience)
# ===========================

output "bucket_names" {
  description = "Map of all bucket names"
  value = {
    data      = aws_s3_bucket.data.bucket
    models    = aws_s3_bucket.models.bucket
    logs      = aws_s3_bucket.logs.bucket
    artifacts = aws_s3_bucket.artifacts.bucket
  }
}

output "bucket_arns" {
  description = "Map of all bucket ARNs"
  value = {
    data      = aws_s3_bucket.data.arn
    models    = aws_s3_bucket.models.arn
    logs      = aws_s3_bucket.logs.arn
    artifacts = aws_s3_bucket.artifacts.arn
  }
}

output "bucket_domain_names" {
  description = "Map of all bucket domain names"
  value = {
    data      = aws_s3_bucket.data.bucket_domain_name
    models    = aws_s3_bucket.models.bucket_domain_name
    logs      = aws_s3_bucket.logs.bucket_domain_name
    artifacts = aws_s3_bucket.artifacts.bucket_domain_name
  }
}

# ===========================
# Configuration Summary
# ===========================

output "bucket_configuration" {
  description = "Summary of bucket configuration"
  value = {
    versioning_enabled    = var.enable_versioning
    encryption_enabled    = var.enable_server_side_encryption
    replication_enabled   = var.enable_cross_region_replication
    notifications_enabled = var.enable_s3_notifications
    lifecycle_configured  = var.lifecycle_expiration_days > 0
    total_buckets         = 4
  }
}

# ===========================
# Access Information
# ===========================

output "s3_sync_commands" {
  description = "AWS CLI commands for syncing data to buckets"
  value = {
    data      = "aws s3 sync ./data/ s3://${aws_s3_bucket.data.bucket}/data/"
    models    = "aws s3 sync ./models/ s3://${aws_s3_bucket.models.bucket}/models/"
    logs      = "aws s3 sync ./logs/ s3://${aws_s3_bucket.logs.bucket}/logs/"
    artifacts = "aws s3 sync ./artifacts/ s3://${aws_s3_bucket.artifacts.bucket}/artifacts/"
  }
}

output "s3_console_urls" {
  description = "AWS Console URLs for S3 buckets"
  value = {
    data      = "https://console.aws.amazon.com/s3/buckets/${aws_s3_bucket.data.bucket}"
    models    = "https://console.aws.amazon.com/s3/buckets/${aws_s3_bucket.models.bucket}"
    logs      = "https://console.aws.amazon.com/s3/buckets/${aws_s3_bucket.logs.bucket}"
    artifacts = "https://console.aws.amazon.com/s3/buckets/${aws_s3_bucket.artifacts.bucket}"
  }
}
