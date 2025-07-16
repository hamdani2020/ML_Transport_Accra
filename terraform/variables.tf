# Terraform Variables Definition
# This file defines all input variables used across the infrastructure

# ===========================
# General Configuration
# ===========================

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ml-transport-accra"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "ml-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

# ===========================
# VPC Configuration
# ===========================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (all resources will be placed in public subnets)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "At least 2 public subnets are required for high availability."
  }
}

variable "enable_vpn_gateway" {
  description = "Enable VPN gateway"
  type        = bool
  default     = false
}

# ===========================
# Security Configuration
# ===========================

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_key_name" {
  description = "Name of the AWS key pair for SSH access"
  type        = string
  default     = ""
}

# ===========================
# EC2 Configuration
# ===========================

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.large"

  validation {
    condition = contains([
      "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge",
      "m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge",
      "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge"
    ], var.instance_type)
    error_message = "Instance type must be a valid EC2 instance type suitable for ML workloads."
  }
}

variable "min_instance_count" {
  description = "Minimum number of instances in Auto Scaling Group"
  type        = number
  default     = 1

  validation {
    condition     = var.min_instance_count >= 1
    error_message = "Minimum instance count must be at least 1."
  }
}

variable "max_instance_count" {
  description = "Maximum number of instances in Auto Scaling Group"
  type        = number
  default     = 3

  validation {
    condition     = var.max_instance_count >= var.min_instance_count
    error_message = "Maximum instance count must be greater than or equal to minimum instance count."
  }
}

variable "desired_instance_count" {
  description = "Desired number of instances in Auto Scaling Group"
  type        = number
  default     = 1
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed monitoring for EC2 instances (disabled to reduce costs)"
  type        = bool
  default     = false
}

variable "health_check_type" {
  description = "Type of health check for Auto Scaling Group"
  type        = string
  default     = "ELB"

  validation {
    condition     = contains(["EC2", "ELB"], var.health_check_type)
    error_message = "Health check type must be either EC2 or ELB."
  }
}

variable "health_check_grace_period" {
  description = "Grace period for health checks (seconds)"
  type        = number
  default     = 300
}

# ===========================
# Application Configuration
# ===========================

variable "application_port" {
  description = "Port for the main application"
  type        = number
  default     = 8000
}

variable "airflow_port" {
  description = "Port for Airflow web interface"
  type        = number
  default     = 8082
}

variable "mlflow_port" {
  description = "Port for MLflow web interface"
  type        = number
  default     = 5000
}

variable "docker_compose_version" {
  description = "Docker Compose version to install"
  type        = string
  default     = "2.20.0"
}

# ===========================
# S3 Configuration
# ===========================

variable "s3_enable_versioning" {
  description = "Enable versioning on S3 buckets"
  type        = bool
  default     = true
}

variable "s3_enable_encryption" {
  description = "Enable server-side encryption on S3 buckets"
  type        = bool
  default     = true
}

variable "s3_lifecycle_expiration_days" {
  description = "Number of days after which objects expire"
  type        = number
  default     = 365
}

variable "s3_transition_to_ia_days" {
  description = "Number of days after which objects transition to IA storage class"
  type        = number
  default     = 30
}

variable "s3_transition_to_glacier_days" {
  description = "Number of days after which objects transition to Glacier storage class"
  type        = number
  default     = 90
}

variable "s3_enable_cross_region_replication" {
  description = "Enable cross-region replication for S3 buckets"
  type        = bool
  default     = false
}

variable "s3_replication_destination_region" {
  description = "Destination region for S3 cross-region replication"
  type        = string
  default     = "us-west-2"
}

# ===========================
# Load Balancer Configuration
# ===========================

variable "enable_load_balancer" {
  description = "Enable Application Load Balancer"
  type        = bool
  default     = true
}

variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for HTTPS"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# ===========================
# Database Configuration
# ===========================

variable "enable_rds" {
  description = "Enable RDS PostgreSQL instance for Airflow"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS instance (GB)"
  type        = number
  default     = 20
}

variable "db_backup_retention_period" {
  description = "Backup retention period for RDS (days)"
  type        = number
  default     = 7
}

# ===========================
# Monitoring Configuration
# ===========================

variable "enable_sns_alerts" {
  description = "Enable SNS alerts for monitoring"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

# ===========================
# Backup Configuration
# ===========================

variable "enable_backup" {
  description = "Enable AWS Backup for EC2 instances"
  type        = bool
  default     = true
}

variable "backup_schedule" {
  description = "Cron expression for backup schedule"
  type        = string
  default     = "cron(0 2 * * ? *)" # Daily at 2 AM UTC
}

variable "backup_retention_days" {
  description = "Backup retention period (days)"
  type        = number
  default     = 30
}

# ===========================
# Cost Optimization
# ===========================

variable "enable_spot_instances" {
  description = "Use EC2 Spot instances for cost optimization"
  type        = bool
  default     = false
}

variable "spot_instance_types" {
  description = "List of instance types for Spot instances"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge", "m5.large", "m5.xlarge"]
}

variable "spot_max_price" {
  description = "Maximum price for Spot instances"
  type        = string
  default     = "0.10"
}

# ===========================
# Development Configuration
# ===========================

variable "enable_ssh_access" {
  description = "Enable SSH access to instances"
  type        = bool
  default     = true
}

variable "enable_public_access" {
  description = "Enable public access to the application"
  type        = bool
  default     = true
}

variable "create_bastion_host" {
  description = "Create a bastion host for secure access"
  type        = bool
  default     = false
}
