# EC2 Module Variables
# This file defines all input variables for the EC2 module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where EC2 instances will be launched"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the load balancer and instances"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of subnet IDs for EC2 instances (using public subnets)"
  type        = list(string)
}

# ===========================
# Instance Configuration
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

variable "key_name" {
  description = "Name of the AWS key pair for SSH access"
  type        = string
  default     = ""
}

variable "security_group_ids" {
  description = "List of security group IDs to attach to instances"
  type        = list(string)
}

variable "iam_instance_profile" {
  description = "Name of the IAM instance profile to attach to instances"
  type        = string
}

# ===========================
# Auto Scaling Configuration
# ===========================

variable "min_size" {
  description = "Minimum number of instances in Auto Scaling Group"
  type        = number
  default     = 1

  validation {
    condition     = var.min_size >= 1
    error_message = "Minimum instance count must be at least 1."
  }
}

variable "max_size" {
  description = "Maximum number of instances in Auto Scaling Group"
  type        = number
  default     = 3

  validation {
    condition     = var.max_size >= var.min_size
    error_message = "Maximum instance count must be greater than or equal to minimum instance count."
  }
}

variable "desired_capacity" {
  description = "Desired number of instances in Auto Scaling Group"
  type        = number
  default     = 1
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
# Storage Configuration
# ===========================

variable "root_volume_type" {
  description = "Type of root volume"
  type        = string
  default     = "gp3"

  validation {
    condition     = contains(["gp2", "gp3", "io1", "io2"], var.root_volume_type)
    error_message = "Root volume type must be one of: gp2, gp3, io1, io2."
  }
}

variable "root_volume_size" {
  description = "Size of root volume in GB"
  type        = number
  default     = 50

  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 1000
    error_message = "Root volume size must be between 20 and 1000 GB."
  }
}

variable "data_volume_size" {
  description = "Size of additional data volume in GB"
  type        = number
  default     = 100

  validation {
    condition     = var.data_volume_size >= 50 && var.data_volume_size <= 2000
    error_message = "Data volume size must be between 50 and 2000 GB."
  }
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

variable "s3_data_bucket_name" {
  description = "Name of the S3 bucket containing GTFS data"
  type        = string
}

variable "s3_models_bucket_name" {
  description = "Name of the S3 bucket for ML models"
  type        = string
}

variable "s3_logs_bucket_name" {
  description = "Name of the S3 bucket for logs"
  type        = string
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

variable "enable_https_redirect" {
  description = "Enable automatic HTTP to HTTPS redirect"
  type        = bool
  default     = false
}

# ===========================
# Monitoring Configuration
# ===========================

variable "enable_detailed_monitoring" {
  description = "Enable detailed monitoring for EC2 instances (disabled to reduce costs)"
  type        = bool
  default     = false
}

# ===========================
# Alerting Configuration
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

variable "target_capacity_utilization" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70

  validation {
    condition     = var.target_capacity_utilization >= 40 && var.target_capacity_utilization <= 90
    error_message = "Target capacity utilization must be between 40 and 90 percent."
  }
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

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

variable "backup_kms_key_id" {
  description = "KMS key ID for backup encryption"
  type        = string
  default     = ""
}

# ===========================
# Spot Instance Configuration
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
  description = "Maximum price for Spot instances (USD per hour)"
  type        = string
  default     = "0.10"
}

variable "spot_allocation_strategy" {
  description = "Allocation strategy for Spot instances"
  type        = string
  default     = "diversified"

  validation {
    condition     = contains(["lowest-price", "diversified"], var.spot_allocation_strategy)
    error_message = "Spot allocation strategy must be either 'lowest-price' or 'diversified'."
  }
}

# ===========================
# Network Configuration
# ===========================

variable "enable_enhanced_networking" {
  description = "Enable enhanced networking (SR-IOV)"
  type        = bool
  default     = true
}

variable "enable_ebs_optimization" {
  description = "Enable EBS optimization"
  type        = bool
  default     = true
}

variable "placement_group_strategy" {
  description = "Placement group strategy for instances"
  type        = string
  default     = ""

  validation {
    condition = var.placement_group_strategy == "" || contains([
      "cluster", "partition", "spread"
    ], var.placement_group_strategy)
    error_message = "Placement group strategy must be one of: cluster, partition, spread, or empty string."
  }
}

# ===========================
# Security Configuration
# ===========================

variable "enable_termination_protection" {
  description = "Enable termination protection for instances"
  type        = bool
  default     = false
}

variable "disable_api_termination" {
  description = "Disable API termination for instances"
  type        = bool
  default     = false
}

variable "enable_instance_metadata_v2" {
  description = "Require IMDSv2 for enhanced security"
  type        = bool
  default     = true
}

# ===========================
# Autoscaling Policies
# ===========================

variable "scale_up_cooldown" {
  description = "Cooldown period for scale up actions (seconds)"
  type        = number
  default     = 300
}

variable "scale_down_cooldown" {
  description = "Cooldown period for scale down actions (seconds)"
  type        = number
  default     = 300
}



# ===========================
# Custom Configuration
# ===========================

variable "custom_ami_id" {
  description = "Custom AMI ID to use instead of the latest Ubuntu AMI"
  type        = string
  default     = ""
}

variable "additional_user_data" {
  description = "Additional user data script to append"
  type        = string
  default     = ""
}

variable "custom_security_group_rules" {
  description = "Additional security group rules"
  type = list(object({
    type        = string
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
