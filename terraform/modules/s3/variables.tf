# S3 Module Variables
# This file defines all input variables for the S3 module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "random_suffix" {
  description = "Random suffix for unique bucket naming"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning on S3 buckets"
  type        = bool
  default     = true
}

variable "enable_server_side_encryption" {
  description = "Enable server-side encryption on S3 buckets"
  type        = bool
  default     = true
}

variable "lifecycle_expiration_days" {
  description = "Number of days after which objects expire"
  type        = number
  default     = 365

  validation {
    condition     = var.lifecycle_expiration_days >= 0
    error_message = "Lifecycle expiration days must be a non-negative number."
  }
}

variable "transition_to_ia_days" {
  description = "Number of days after which objects transition to IA storage class"
  type        = number
  default     = 30

  validation {
    condition     = var.transition_to_ia_days >= 0
    error_message = "Transition to IA days must be a non-negative number."
  }
}

variable "transition_to_glacier_days" {
  description = "Number of days after which objects transition to Glacier storage class"
  type        = number
  default     = 90

  validation {
    condition     = var.transition_to_glacier_days >= var.transition_to_ia_days
    error_message = "Transition to Glacier days must be greater than or equal to transition to IA days."
  }
}

variable "enable_cross_region_replication" {
  description = "Enable cross-region replication for S3 buckets"
  type        = bool
  default     = false
}

variable "replication_destination_region" {
  description = "Destination region for S3 cross-region replication"
  type        = string
  default     = "us-west-2"
}

variable "enable_s3_notifications" {
  description = "Enable S3 bucket notifications"
  type        = bool
  default     = false
}

variable "kms_key_id" {
  description = "KMS key ID for S3 bucket encryption (optional)"
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Force destroy S3 buckets even if they contain objects"
  type        = bool
  default     = false
}

variable "object_lock_enabled" {
  description = "Enable S3 Object Lock"
  type        = bool
  default     = false
}

variable "object_lock_retention_days" {
  description = "Object lock retention period in days"
  type        = number
  default     = 365
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = []
}

variable "cors_allowed_methods" {
  description = "List of allowed methods for CORS"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "List of headers to expose for CORS"
  type        = list(string)
  default     = ["ETag"]
}

variable "cors_max_age_seconds" {
  description = "Max age in seconds for CORS preflight requests"
  type        = number
  default     = 3600
}

variable "intelligent_tiering_enabled" {
  description = "Enable S3 Intelligent Tiering"
  type        = bool
  default     = false
}

variable "inventory_enabled" {
  description = "Enable S3 inventory reporting"
  type        = bool
  default     = false
}

variable "inventory_frequency" {
  description = "Frequency of inventory reports (Daily or Weekly)"
  type        = string
  default     = "Weekly"

  validation {
    condition     = contains(["Daily", "Weekly"], var.inventory_frequency)
    error_message = "Inventory frequency must be either Daily or Weekly."
  }
}

variable "logging_target_bucket" {
  description = "Target bucket for S3 access logging"
  type        = string
  default     = ""
}

variable "logging_target_prefix" {
  description = "Prefix for S3 access logs"
  type        = string
  default     = "access-logs/"
}

variable "enable_transfer_acceleration" {
  description = "Enable S3 Transfer Acceleration"
  type        = bool
  default     = false
}

variable "request_payer" {
  description = "Who pays for requests (BucketOwner or Requester)"
  type        = string
  default     = "BucketOwner"

  validation {
    condition     = contains(["BucketOwner", "Requester"], var.request_payer)
    error_message = "Request payer must be either BucketOwner or Requester."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Bucket-specific configurations
variable "data_bucket_cors_enabled" {
  description = "Enable CORS for data bucket"
  type        = bool
  default     = true
}

variable "models_bucket_cors_enabled" {
  description = "Enable CORS for models bucket"
  type        = bool
  default     = false
}

variable "logs_bucket_cors_enabled" {
  description = "Enable CORS for logs bucket"
  type        = bool
  default     = false
}

variable "artifacts_bucket_cors_enabled" {
  description = "Enable CORS for artifacts bucket"
  type        = bool
  default     = false
}
