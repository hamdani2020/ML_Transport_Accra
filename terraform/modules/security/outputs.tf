# Security Module Outputs
# This file defines all output values from the Security module

# ===========================
# Security Group Outputs
# ===========================

output "application_security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.application.id
}

output "application_security_group_arn" {
  description = "ARN of the application security group"
  value       = aws_security_group.application.arn
}

output "application_security_group_name" {
  description = "Name of the application security group"
  value       = aws_security_group.application.name
}

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "alb_security_group_arn" {
  description = "ARN of the ALB security group"
  value       = aws_security_group.alb.arn
}

output "alb_security_group_name" {
  description = "Name of the ALB security group"
  value       = aws_security_group.alb.name
}

output "database_security_group_id" {
  description = "ID of the database security group"
  value       = var.enable_database_sg ? aws_security_group.database[0].id : null
}

output "database_security_group_arn" {
  description = "ARN of the database security group"
  value       = var.enable_database_sg ? aws_security_group.database[0].arn : null
}

output "bastion_security_group_id" {
  description = "ID of the bastion security group"
  value       = var.enable_bastion_sg ? aws_security_group.bastion[0].id : null
}

output "bastion_security_group_arn" {
  description = "ARN of the bastion security group"
  value       = var.enable_bastion_sg ? aws_security_group.bastion[0].arn : null
}

# ===========================
# IAM Role and Policy Outputs
# ===========================

output "ec2_instance_role_arn" {
  description = "ARN of the EC2 instance IAM role"
  value       = aws_iam_role.ec2_instance_role.arn
}

output "ec2_instance_role_name" {
  description = "Name of the EC2 instance IAM role"
  value       = aws_iam_role.ec2_instance_role.name
}

output "ec2_instance_profile_arn" {
  description = "ARN of the EC2 instance profile"
  value       = aws_iam_instance_profile.ec2_instance_profile.arn
}

output "ec2_instance_profile_name" {
  description = "Name of the EC2 instance profile"
  value       = aws_iam_instance_profile.ec2_instance_profile.name
}

output "ec2_instance_role_id" {
  description = "ID of the EC2 instance IAM role"
  value       = aws_iam_role.ec2_instance_role.id
}

# ===========================
# Key Pair Outputs
# ===========================

output "key_pair_name" {
  description = "Name of the created key pair"
  value       = var.create_key_pair ? aws_key_pair.ec2_key[0].key_name : var.ssh_key_name
}

output "key_pair_fingerprint" {
  description = "Fingerprint of the key pair"
  value       = var.create_key_pair ? aws_key_pair.ec2_key[0].fingerprint : null
}

output "private_key_secret_arn" {
  description = "ARN of the secret containing the private key"
  value       = var.create_key_pair && var.store_key_in_secrets_manager ? aws_secretsmanager_secret.ec2_private_key[0].arn : null
}

output "private_key_secret_name" {
  description = "Name of the secret containing the private key"
  value       = var.create_key_pair && var.store_key_in_secrets_manager ? aws_secretsmanager_secret.ec2_private_key[0].name : null
}

# For development purposes only - DO NOT USE IN PRODUCTION
output "private_key_pem" {
  description = "Private key in PEM format (for development only)"
  value       = var.create_key_pair && var.environment == "dev" ? tls_private_key.ec2_key[0].private_key_pem : null
  sensitive   = true
}

# ===========================
# WAF Outputs
# ===========================

output "waf_web_acl_id" {
  description = "ID of the WAF Web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].id : null
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null
}

output "waf_web_acl_name" {
  description = "Name of the WAF Web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].name : null
}

# ===========================
# Security Group Rule Summaries
# ===========================

output "security_group_rules_summary" {
  description = "Summary of security group rules"
  value = {
    application_ports = [
      {
        port        = var.application_port
        protocol    = "tcp"
        description = "FastAPI application"
      },
      {
        port        = var.airflow_port
        protocol    = "tcp"
        description = "Airflow web interface"
      },
      {
        port        = var.mlflow_port
        protocol    = "tcp"
        description = "MLflow web interface"
      }
    ]
    ssh_enabled      = var.enable_ssh_access
    https_enabled    = true
    database_enabled = var.enable_database_sg
    bastion_enabled  = var.enable_bastion_sg
  }
}

# ===========================
# IAM Policy Summaries
# ===========================

output "iam_policies_attached" {
  description = "List of IAM policies attached to EC2 role"
  value = [
    "S3 Access Policy",
    "SSM Access Policy",
    var.enable_ecr_access ? "ECR Access Policy" : null,
    var.enable_sns_access ? "SNS Publish Policy" : null,
    var.enable_secrets_manager_access ? "Secrets Manager Policy" : null
  ]
}

# ===========================
# Security Configuration Summary
# ===========================

output "security_configuration" {
  description = "Summary of security configuration"
  value = {
    ssh_access_enabled      = var.enable_ssh_access
    waf_enabled             = var.enable_waf
    database_sg_enabled     = var.enable_database_sg
    bastion_sg_enabled      = var.enable_bastion_sg
    ecr_access_enabled      = var.enable_ecr_access
    secrets_manager_enabled = var.enable_secrets_manager_access
    key_pair_created        = var.create_key_pair
    key_stored_in_secrets   = var.store_key_in_secrets_manager
    production_hardening    = var.production_hardening
    compliance_framework    = var.compliance_framework
    cloudwatch_disabled     = true
  }
}

# ===========================
# Access Information
# ===========================

output "ssh_access_info" {
  description = "Information about SSH access"
  value = {
    key_name          = var.create_key_pair ? aws_key_pair.ec2_key[0].key_name : var.ssh_key_name
    ssh_enabled       = var.enable_ssh_access
    allowed_cidrs     = var.ssh_allowed_cidrs
    port              = 22
    connection_method = var.create_key_pair && var.store_key_in_secrets_manager ? "Use key from Secrets Manager" : "Use existing key pair"
  }
}

output "application_access_info" {
  description = "Information about application access"
  value = {
    application_port = var.application_port
    airflow_port     = var.airflow_port
    mlflow_port      = var.mlflow_port
    https_enabled    = var.enable_https_redirect
    waf_protected    = var.enable_waf
    allowed_cidrs    = var.allowed_cidr_blocks
  }
}

# ===========================
# Security Recommendations
# ===========================

output "security_recommendations" {
  description = "Security recommendations based on current configuration"
  value = {
    warnings = compact([
      var.allowed_cidr_blocks[0] == "0.0.0.0/0" && var.environment == "prod" ? "Consider restricting access from 0.0.0.0/0 in production" : null,
      !var.enable_waf && var.environment == "prod" ? "Consider enabling WAF for production environments" : null,
      !var.production_hardening && var.environment == "prod" ? "Consider enabling production hardening" : null,
      var.ssh_allowed_cidrs[0] == "0.0.0.0/0" && var.environment == "prod" ? "Consider restricting SSH access in production" : null
    ])

    recommendations = compact([
      var.environment == "prod" && !var.enable_guardduty ? "Enable GuardDuty for threat detection" : null,
      var.environment == "prod" && !var.enable_cloudtrail ? "Enable CloudTrail for audit logging" : null,
      var.environment == "prod" && !var.enable_config ? "Enable AWS Config for compliance" : null,
      var.compliance_framework == "none" && var.environment == "prod" ? "Consider setting compliance framework" : null
    ])
  }
}

# ===========================
# Resource ARNs for Cross-Module Reference
# ===========================

output "all_security_group_ids" {
  description = "Map of all security group IDs"
  value = {
    application = aws_security_group.application.id
    alb         = aws_security_group.alb.id
    database    = var.enable_database_sg ? aws_security_group.database[0].id : null
    bastion     = var.enable_bastion_sg ? aws_security_group.bastion[0].id : null
  }
}

output "all_security_group_arns" {
  description = "Map of all security group ARNs"
  value = {
    application = aws_security_group.application.arn
    alb         = aws_security_group.alb.arn
    database    = var.enable_database_sg ? aws_security_group.database[0].arn : null
    bastion     = var.enable_bastion_sg ? aws_security_group.bastion[0].arn : null
  }
}
