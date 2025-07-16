# Security Module Variables
# This file defines all input variables for the Security module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where security groups will be created"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}

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
# SSH and Access Configuration
# ===========================

variable "enable_ssh_access" {
  description = "Enable SSH access to instances"
  type        = bool
  default     = true
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "bastion_allowed_cidrs" {
  description = "CIDR blocks allowed to access bastion host"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ===========================
# Security Group Toggles
# ===========================

variable "enable_database_sg" {
  description = "Enable database security group"
  type        = bool
  default     = false
}

variable "enable_bastion_sg" {
  description = "Enable bastion host security group"
  type        = bool
  default     = false
}

variable "database_allowed_cidrs" {
  description = "CIDR blocks allowed to access database"
  type        = list(string)
  default     = []
}

# ===========================
# IAM Permissions
# ===========================

variable "enable_ecr_access" {
  description = "Enable ECR access for EC2 instances"
  type        = bool
  default     = true
}

variable "enable_sns_access" {
  description = "Enable SNS publish access for EC2 instances"
  type        = bool
  default     = true
}

variable "enable_secrets_manager_access" {
  description = "Enable Secrets Manager access for EC2 instances"
  type        = bool
  default     = true
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs that EC2 instances need access to"
  type        = list(string)
  default     = []
}

variable "additional_iam_policies" {
  description = "Additional IAM policy ARNs to attach to EC2 role"
  type        = list(string)
  default     = []
}

# ===========================
# Key Pair Configuration
# ===========================

variable "create_key_pair" {
  description = "Create a new EC2 key pair"
  type        = bool
  default     = false
}

variable "store_key_in_secrets_manager" {
  description = "Store the private key in AWS Secrets Manager"
  type        = bool
  default     = true
}

# ===========================
# WAF Configuration
# ===========================

variable "enable_waf" {
  description = "Enable AWS WAF for additional security"
  type        = bool
  default     = false
}

variable "waf_rate_limit" {
  description = "Rate limit for WAF (requests per 5 minutes)"
  type        = number
  default     = 2000

  validation {
    condition     = var.waf_rate_limit >= 100 && var.waf_rate_limit <= 20000000
    error_message = "WAF rate limit must be between 100 and 20,000,000."
  }
}

variable "waf_blocked_countries" {
  description = "List of country codes to block in WAF"
  type        = list(string)
  default     = []
}

variable "waf_allowed_countries" {
  description = "List of country codes to allow in WAF (empty means all)"
  type        = list(string)
  default     = []
}

# ===========================
# Application Ports
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

variable "additional_ports" {
  description = "Additional ports to open in security groups"
  type = list(object({
    port        = number
    protocol    = string
    description = string
    cidr_blocks = list(string)
  }))
  default = []
}

# ===========================
# Load Balancer Configuration
# ===========================

variable "enable_https_redirect" {
  description = "Enable automatic HTTP to HTTPS redirect"
  type        = bool
  default     = false
}

variable "ssl_policy" {
  description = "SSL policy for ALB listeners"
  type        = string
  default     = "ELBSecurityPolicy-TLS-1-2-2017-01"

  validation {
    condition = contains([
      "ELBSecurityPolicy-TLS-1-2-2017-01",
      "ELBSecurityPolicy-TLS-1-2-Ext-2018-06",
      "ELBSecurityPolicy-FS-2018-06",
      "ELBSecurityPolicy-FS-1-2-Res-2020-10"
    ], var.ssl_policy)
    error_message = "SSL policy must be a valid ALB SSL policy."
  }
}

# ===========================
# Network Security
# ===========================

variable "enable_flow_logs" {
  description = "Enable VPC flow logs for security monitoring"
  type        = bool
  default     = false
}

variable "enable_network_acls" {
  description = "Enable custom network ACLs"
  type        = bool
  default     = false
}

variable "block_tor_exit_nodes" {
  description = "Block traffic from known Tor exit nodes"
  type        = bool
  default     = false
}

variable "enable_ddos_protection" {
  description = "Enable AWS Shield Advanced for DDoS protection"
  type        = bool
  default     = false
}

# ===========================
# Monitoring and Alerting
# ===========================

variable "enable_security_monitoring" {
  description = "Enable security monitoring and alerting"
  type        = bool
  default     = true
}

variable "security_alert_email" {
  description = "Email address for security alerts"
  type        = string
  default     = ""
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty for threat detection"
  type        = bool
  default     = false
}

variable "enable_config" {
  description = "Enable AWS Config for compliance monitoring"
  type        = bool
  default     = false
}

# ===========================
# Compliance and Audit
# ===========================

variable "enable_cloudtrail" {
  description = "Enable CloudTrail for API logging"
  type        = bool
  default     = false
}

variable "cloudtrail_s3_bucket" {
  description = "S3 bucket for CloudTrail logs"
  type        = string
  default     = ""
}

variable "compliance_framework" {
  description = "Compliance framework requirements (e.g., SOC2, HIPAA, PCI-DSS)"
  type        = string
  default     = "none"

  validation {
    condition     = contains(["none", "soc2", "hipaa", "pci-dss", "gdpr"], var.compliance_framework)
    error_message = "Compliance framework must be one of: none, soc2, hipaa, pci-dss, gdpr."
  }
}

# ===========================
# Backup and Recovery
# ===========================

variable "enable_backup_encryption" {
  description = "Enable encryption for backups"
  type        = bool
  default     = true
}

variable "backup_kms_key_id" {
  description = "KMS key ID for backup encryption"
  type        = string
  default     = ""
}

# ===========================
# Environment-specific Settings
# ===========================

variable "production_hardening" {
  description = "Apply production hardening rules"
  type        = bool
  default     = false
}

variable "development_access" {
  description = "Enable development-specific access patterns"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
