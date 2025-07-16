# EC2 Module Outputs
# This file defines all output values from the EC2 module

# ===========================
# Launch Template Outputs
# ===========================

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.main.id
}

output "launch_template_arn" {
  description = "ARN of the launch template"
  value       = aws_launch_template.main.arn
}

output "launch_template_name" {
  description = "Name of the launch template"
  value       = aws_launch_template.main.name
}

output "launch_template_latest_version" {
  description = "Latest version of the launch template"
  value       = aws_launch_template.main.latest_version
}

# ===========================
# Auto Scaling Group Outputs
# ===========================

output "auto_scaling_group_id" {
  description = "ID of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.id
}

output "auto_scaling_group_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.name
}

output "auto_scaling_group_arn" {
  description = "ARN of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.arn
}

output "auto_scaling_group_availability_zones" {
  description = "Availability zones used by the Auto Scaling Group"
  value       = aws_autoscaling_group.main.availability_zones
}

output "auto_scaling_group_min_size" {
  description = "Minimum size of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.min_size
}

output "auto_scaling_group_max_size" {
  description = "Maximum size of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.max_size
}

output "auto_scaling_group_desired_capacity" {
  description = "Desired capacity of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.desired_capacity
}

# ===========================
# Load Balancer Outputs
# ===========================

output "load_balancer_id" {
  description = "ID of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].id : null
}

output "load_balancer_arn" {
  description = "ARN of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].arn : null
}

output "load_balancer_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].arn_suffix : null
}

output "load_balancer_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].dns_name : null
}

output "load_balancer_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].zone_id : null
}

output "load_balancer_hosted_zone_id" {
  description = "Hosted zone ID of the Application Load Balancer"
  value       = var.enable_load_balancer ? aws_lb.main[0].zone_id : null
}

# ===========================
# Target Group Outputs
# ===========================

output "target_group_app_arn" {
  description = "ARN of the application target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.app[0].arn : null
}

output "target_group_app_arn_suffix" {
  description = "ARN suffix of the application target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.app[0].arn_suffix : null
}

output "target_group_airflow_arn" {
  description = "ARN of the Airflow target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.airflow[0].arn : null
}

output "target_group_airflow_arn_suffix" {
  description = "ARN suffix of the Airflow target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.airflow[0].arn_suffix : null
}

output "target_group_mlflow_arn" {
  description = "ARN of the MLflow target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.mlflow[0].arn : null
}

output "target_group_mlflow_arn_suffix" {
  description = "ARN suffix of the MLflow target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.mlflow[0].arn_suffix : null
}

# For backward compatibility
output "target_group_arn" {
  description = "ARN of the main application target group"
  value       = var.enable_load_balancer ? aws_lb_target_group.app[0].arn : null
}

# ===========================
# CloudWatch Outputs (Disabled)
# ===========================

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group (disabled)"
  value       = null
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group (disabled)"
  value       = null
}

output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard (disabled)"
  value       = null
}

# ===========================
# Auto Scaling Policy Outputs
# ===========================

output "target_tracking_policy_arn" {
  description = "ARN of the target tracking scaling policy"
  value       = aws_autoscaling_policy.target_tracking.arn
}

# ===========================
# Auto Scaling Policy Outputs (Simplified)
# ===========================

output "scaling_policy_name" {
  description = "Name of the auto scaling policy"
  value       = aws_autoscaling_policy.target_tracking.name
}

# ===========================
# SNS Outputs
# ===========================

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = var.enable_sns_alerts ? aws_sns_topic.alerts[0].arn : null
}

output "sns_topic_name" {
  description = "Name of the SNS topic for alerts"
  value       = var.enable_sns_alerts ? aws_sns_topic.alerts[0].name : null
}

# ===========================
# Backup Outputs
# ===========================

output "backup_vault_arn" {
  description = "ARN of the backup vault"
  value       = var.enable_backup ? aws_backup_vault.main[0].arn : null
}

output "backup_plan_arn" {
  description = "ARN of the backup plan"
  value       = var.enable_backup ? aws_backup_plan.main[0].arn : null
}

output "backup_plan_id" {
  description = "ID of the backup plan"
  value       = var.enable_backup ? aws_backup_plan.main[0].id : null
}

# ===========================
# Application URLs
# ===========================

output "application_urls" {
  description = "URLs to access the applications"
  value = var.enable_load_balancer ? {
    main_application = "http://${aws_lb.main[0].dns_name}:${var.application_port}"
    airflow          = "http://${aws_lb.main[0].dns_name}:${var.airflow_port}"
    mlflow           = "http://${aws_lb.main[0].dns_name}:${var.mlflow_port}"
    dashboard        = "http://${aws_lb.main[0].dns_name}:${var.application_port}/dashboard"
    api_docs         = "http://${aws_lb.main[0].dns_name}:${var.application_port}/docs"
  } : {}
}

# ===========================
# Instance Information
# ===========================

output "ami_id" {
  description = "AMI ID used for instances"
  value       = data.aws_ami.ubuntu.id
}

output "instance_type" {
  description = "Instance type used"
  value       = var.instance_type
}

output "key_name" {
  description = "Key pair name used for instances"
  value       = var.key_name
}

# ===========================
# Health Check Information
# ===========================

output "health_check_endpoints" {
  description = "Health check endpoints for each service"
  value = {
    main_application = "/health"
    airflow          = "/health"
    mlflow           = "/"
  }
}

output "load_balancer_health_check" {
  description = "Load balancer health check configuration"
  value = var.enable_load_balancer ? {
    app_target_group = {
      port                = var.application_port
      protocol            = "HTTP"
      path                = "/health"
      healthy_threshold   = 2
      unhealthy_threshold = 2
      timeout             = 5
      interval            = 30
    }
    airflow_target_group = {
      port                = var.airflow_port
      protocol            = "HTTP"
      path                = "/health"
      healthy_threshold   = 2
      unhealthy_threshold = 3
      timeout             = 5
      interval            = 30
    }
    mlflow_target_group = {
      port                = var.mlflow_port
      protocol            = "HTTP"
      path                = "/"
      healthy_threshold   = 2
      unhealthy_threshold = 3
      timeout             = 5
      interval            = 30
    }
  } : {}
}

# ===========================
# Configuration Summary
# ===========================

output "deployment_configuration" {
  description = "Summary of deployment configuration"
  value = {
    instance_type          = var.instance_type
    min_instances          = var.min_size
    max_instances          = var.max_size
    desired_instances      = var.desired_capacity
    load_balancer_enabled  = var.enable_load_balancer
    detailed_monitoring    = var.enable_detailed_monitoring
    sns_alerts_enabled     = var.enable_sns_alerts
    backup_enabled         = var.enable_backup
    spot_instances_enabled = var.enable_spot_instances
    root_volume_size       = var.root_volume_size
    data_volume_size       = var.data_volume_size
    application_port       = var.application_port
    airflow_port           = var.airflow_port
    mlflow_port            = var.mlflow_port
  }
}

# ===========================
# Security Information
# ===========================

output "security_information" {
  description = "Security-related information"
  value = {
    security_groups        = var.security_group_ids
    iam_instance_profile   = var.iam_instance_profile
    key_name               = var.key_name
    termination_protection = var.enable_termination_protection
    metadata_v2_required   = var.enable_instance_metadata_v2
    ebs_encryption_enabled = true
    detailed_monitoring    = var.enable_detailed_monitoring
  }
}

# ===========================
# Cost Information
# ===========================

output "cost_optimization" {
  description = "Cost optimization features enabled"
  value = {
    spot_instances_enabled = var.enable_spot_instances
    instance_type          = var.instance_type
    min_instances          = var.min_size
    max_instances          = var.max_size
    ebs_optimized          = var.enable_ebs_optimization
    backup_enabled         = var.enable_backup
    cloudwatch_disabled    = true
  }
}

# ===========================
# Troubleshooting Information
# ===========================

output "troubleshooting_info" {
  description = "Information for troubleshooting"
  value = {
    user_data_log_location = "/var/log/user-data.log"
    application_log_group  = null
    health_check_script    = "/home/ubuntu/health-check.sh"
    deployment_marker      = "s3://${var.s3_data_bucket_name}/deployments/completion-markers/"
    docker_compose_path    = "/home/ubuntu/ml-transport-accra/docker-compose.yml"
    environment_file       = "/home/ubuntu/.env"
    local_logs_path        = "/home/ubuntu/ml-transport-accra/logs/"
  }
}
