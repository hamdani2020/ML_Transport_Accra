# Terraform Outputs Definition
# This file defines all output values from the infrastructure

# ===========================
# VPC Outputs
# ===========================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets (empty - all subnets are public)"
  value       = []
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = module.vpc.internet_gateway_id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

# ===========================
# Security Outputs
# ===========================

output "application_security_group_id" {
  description = "ID of the application security group"
  value       = module.security.application_security_group_id
}

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = module.security.alb_security_group_id
}

output "ec2_instance_profile_name" {
  description = "Name of the EC2 instance profile"
  value       = module.security.ec2_instance_profile_name
}

output "ec2_instance_role_arn" {
  description = "ARN of the EC2 instance role"
  value       = module.security.ec2_instance_role_arn
}

# ===========================
# S3 Outputs
# ===========================

output "s3_data_bucket_name" {
  description = "Name of the S3 data bucket"
  value       = module.s3.data_bucket_name
}

output "s3_data_bucket_arn" {
  description = "ARN of the S3 data bucket"
  value       = module.s3.data_bucket_arn
}

output "s3_models_bucket_name" {
  description = "Name of the S3 models bucket"
  value       = module.s3.models_bucket_name
}

output "s3_models_bucket_arn" {
  description = "ARN of the S3 models bucket"
  value       = module.s3.models_bucket_arn
}

output "s3_logs_bucket_name" {
  description = "Name of the S3 logs bucket"
  value       = module.s3.logs_bucket_name
}

output "s3_logs_bucket_arn" {
  description = "ARN of the S3 logs bucket"
  value       = module.s3.logs_bucket_arn
}

output "s3_artifacts_bucket_name" {
  description = "Name of the S3 artifacts bucket"
  value       = module.s3.artifacts_bucket_name
}

output "s3_artifacts_bucket_arn" {
  description = "ARN of the S3 artifacts bucket"
  value       = module.s3.artifacts_bucket_arn
}

# ===========================
# EC2 Outputs
# ===========================

output "launch_template_id" {
  description = "ID of the launch template"
  value       = module.ec2.launch_template_id
}

output "auto_scaling_group_name" {
  description = "Name of the Auto Scaling Group"
  value       = module.ec2.auto_scaling_group_name
}

output "auto_scaling_group_arn" {
  description = "ARN of the Auto Scaling Group"
  value       = module.ec2.auto_scaling_group_arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = module.ec2.target_group_arn
}

# ===========================
# Load Balancer Outputs
# ===========================

output "load_balancer_arn" {
  description = "ARN of the Application Load Balancer"
  value       = module.ec2.load_balancer_arn
}

output "load_balancer_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.ec2.load_balancer_dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = module.ec2.load_balancer_zone_id
}

# ===========================
# Application URLs
# ===========================

output "application_url" {
  description = "URL to access the main application"
  value       = "http://${module.ec2.load_balancer_dns_name}:8000"
}

output "airflow_url" {
  description = "URL to access Airflow web interface"
  value       = "http://${module.ec2.load_balancer_dns_name}:8082"
}

output "mlflow_url" {
  description = "URL to access MLflow web interface"
  value       = "http://${module.ec2.load_balancer_dns_name}:5000"
}

output "dashboard_url" {
  description = "URL to access the transport analysis dashboard"
  value       = "http://${module.ec2.load_balancer_dns_name}:8000/dashboard"
}

output "api_docs_url" {
  description = "URL to access API documentation"
  value       = "http://${module.ec2.load_balancer_dns_name}:8000/docs"
}

# ===========================
# CloudWatch Outputs
# ===========================

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = module.ec2.cloudwatch_log_group_name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = module.ec2.cloudwatch_log_group_arn
}

# ===========================
# SNS Outputs
# ===========================

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = module.ec2.sns_topic_arn
  sensitive   = false
}

# ===========================
# Deployment Information
# ===========================

output "deployment_info" {
  description = "Information about the deployment"
  value = {
    project_name      = var.project_name
    environment       = var.environment
    aws_region        = var.aws_region
    deployed_at       = timestamp()
    terraform_version = ">=1.5.0"
  }
}

# ===========================
# Resource Tags
# ===========================

output "common_tags" {
  description = "Common tags applied to all resources"
  value = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
    Repository  = "ML_Transport_Accra"
  }
}

# ===========================
# Connection Information
# ===========================

output "ssh_connection_command" {
  description = "SSH command to connect to instances (if SSH key is configured)"
  value       = var.ssh_key_name != "" ? "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@<instance-ip>" : "SSH key not configured"
}

output "aws_cli_s3_sync_command" {
  description = "AWS CLI command to sync data to S3"
  value       = "aws s3 sync ./data/ s3://${module.s3.data_bucket_name}/data/ --region ${var.aws_region}"
}

# ===========================
# Cost Estimation
# ===========================

output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (approximate)"
  value = {
    ec2_instances  = "~$${var.desired_instance_count * (var.instance_type == \"t3.medium\" ? 67 : 134)}/month"
    load_balancer  = "~$23/month"
    nat_gateway    = "$0/month"
    s3_storage     = "~$23/TB/month"
    data_transfer  = "~$90/TB/month"
    total_estimate = "Starting from ~$135/month (varies by usage)"
  }
}

# ===========================
# Security Information
# ===========================

output "security_recommendations" {
  description = "Security recommendations for the deployment"
  value = {
    ssh_access    = var.ssh_key_name != "" ? "SSH access enabled with key pair" : "No SSH key configured"
    public_access = var.enable_public_access ? "Application is publicly accessible" : "Application is private"
    encryption    = "All S3 buckets encrypted at rest"
    monitoring    = "CloudWatch monitoring enabled"
    backup        = var.enable_backup ? "Automated backups enabled" : "Backups disabled"
  }
}

# ===========================
# Next Steps
# ===========================

output "next_steps" {
  description = "Next steps after deployment"
  value = [
    "1. Access the application at: http://${module.ec2.load_balancer_dns_name}:8000",
    "2. Access Airflow at: http://${module.ec2.load_balancer_dns_name}:8082 (admin/admin)",
    "3. Access MLflow at: http://${module.ec2.load_balancer_dns_name}:5000",
    "4. Upload additional data to S3: aws s3 sync ./data/ s3://${module.s3.data_bucket_name}/",
    "5. Monitor logs in CloudWatch: aws logs describe-log-groups --region ${var.aws_region}",
    "6. Scale instances if needed: terraform apply -var='desired_instance_count=2'",
    "7. Set up domain name and SSL certificate for production use"
  ]
}
