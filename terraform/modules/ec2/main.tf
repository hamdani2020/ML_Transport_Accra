# EC2 Module - Main Configuration
# Creates EC2 instances, Auto Scaling Group, Load Balancer, and related resources

locals {
  # Common tags for all EC2 resources
  ec2_tags = merge(var.tags, {
    Component = "ec2"
    Module    = "ec2"
  })

  # User data script for instance initialization
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    s3_data_bucket         = var.s3_data_bucket_name
    s3_models_bucket       = var.s3_models_bucket_name
    s3_logs_bucket         = var.s3_logs_bucket_name
    aws_region             = data.aws_region.current.name
    environment            = var.environment
    project_name           = var.project_name
    application_port       = var.application_port
    airflow_port           = var.airflow_port
    mlflow_port            = var.mlflow_port
    docker_compose_version = var.docker_compose_version
  }))
}

# Get current AWS region
data "aws_region" "current" {}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ===========================
# Launch Template
# ===========================

resource "aws_launch_template" "main" {
  name_prefix   = "${var.project_name}-${var.environment}-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = var.security_group_ids

  iam_instance_profile {
    name = var.iam_instance_profile
  }

  user_data = local.user_data

  # EBS optimization
  ebs_optimized = true

  # Instance metadata options
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  # Monitoring disabled
  monitoring {
    enabled = false
  }

  # Block device mappings
  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_type           = var.root_volume_type
      volume_size           = var.root_volume_size
      encrypted             = true
      delete_on_termination = true
    }
  }

  # Additional data volume for ML artifacts
  block_device_mappings {
    device_name = "/dev/sdf"
    ebs {
      volume_type           = "gp3"
      volume_size           = var.data_volume_size
      encrypted             = true
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.ec2_tags, {
      Name = "${var.project_name}-${var.environment}-instance"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.ec2_tags, {
      Name = "${var.project_name}-${var.environment}-volume"
    })
  }

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-launch-template"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ===========================
# Application Load Balancer
# ===========================

resource "aws_lb" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_ids[0]] # ALB security group
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod" ? true : false

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-alb"
  })
}

# Target Group for main application
resource "aws_lb_target_group" "app" {
  count = var.enable_load_balancer ? 1 : 0

  name     = "${var.project_name}-${var.environment}-app-tg"
  port     = var.application_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
  }

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-app-tg"
  })
}

# Target Group for Airflow
resource "aws_lb_target_group" "airflow" {
  count = var.enable_load_balancer ? 1 : 0

  name     = "${var.project_name}-${var.environment}-airflow-tg"
  port     = var.airflow_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-airflow-tg"
  })
}

# Target Group for MLflow
resource "aws_lb_target_group" "mlflow" {
  count = var.enable_load_balancer ? 1 : 0

  name     = "${var.project_name}-${var.environment}-mlflow-tg"
  port     = var.mlflow_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-mlflow-tg"
  })
}

# ALB Listener for main application
resource "aws_lb_listener" "app" {
  count = var.enable_load_balancer ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "8000"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app[0].arn
  }

  tags = local.ec2_tags
}

# ALB Listener for Airflow
resource "aws_lb_listener" "airflow" {
  count = var.enable_load_balancer ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "8082"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.airflow[0].arn
  }

  tags = local.ec2_tags
}

# ALB Listener for MLflow
resource "aws_lb_listener" "mlflow" {
  count = var.enable_load_balancer ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "5000"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mlflow[0].arn
  }

  tags = local.ec2_tags
}

# ===========================
# Auto Scaling Group
# ===========================

resource "aws_autoscaling_group" "main" {
  name                = "${var.project_name}-${var.environment}-asg"
  vpc_zone_identifier = var.public_subnet_ids
  target_group_arns = var.enable_load_balancer ? [
    aws_lb_target_group.app[0].arn,
    aws_lb_target_group.airflow[0].arn,
    aws_lb_target_group.mlflow[0].arn
  ] : []
  health_check_type         = var.health_check_type
  health_check_grace_period = var.health_check_grace_period

  min_size         = var.min_size
  max_size         = var.max_size
  desired_capacity = var.desired_capacity

  launch_template {
    id      = aws_launch_template.main.id
    version = "$Latest"
  }

  # Instance refresh configuration
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-asg-instance"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = local.ec2_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ===========================
# Auto Scaling Policies
# ===========================

# Basic target tracking scaling policy based on CPU utilization
resource "aws_autoscaling_policy" "target_tracking" {
  name                   = "${var.project_name}-${var.environment}-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.main.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# ===========================
# SNS Topic for Alerts
# ===========================

resource "aws_sns_topic" "alerts" {
  count = var.enable_sns_alerts ? 1 : 0

  name = "${var.project_name}-${var.environment}-alerts"

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-alerts"
  })
}

resource "aws_sns_topic_subscription" "email_alerts" {
  count = var.enable_sns_alerts && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ===========================
# AWS Backup Configuration
# ===========================

resource "aws_backup_vault" "main" {
  count = var.enable_backup ? 1 : 0

  name        = "${var.project_name}-${var.environment}-backup-vault"
  kms_key_arn = var.backup_kms_key_id

  tags = merge(local.ec2_tags, {
    Name = "${var.project_name}-${var.environment}-backup-vault"
  })
}

resource "aws_backup_plan" "main" {
  count = var.enable_backup ? 1 : 0

  name = "${var.project_name}-${var.environment}-backup-plan"

  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = var.backup_schedule

    recovery_point_tags = merge(local.ec2_tags, {
      BackupType = "Automated"
    })

    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_retention_days
    }
  }

  tags = local.ec2_tags
}

resource "aws_backup_selection" "main" {
  count = var.enable_backup ? 1 : 0

  iam_role_arn = aws_iam_role.backup[0].arn
  name         = "${var.project_name}-${var.environment}-backup-selection"
  plan_id      = aws_backup_plan.main[0].id

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Project"
    value = var.project_name
  }

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Environment"
    value = var.environment
  }
}

# IAM role for AWS Backup
resource "aws_iam_role" "backup" {
  count = var.enable_backup ? 1 : 0

  name = "${var.project_name}-${var.environment}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })

  tags = local.ec2_tags
}

resource "aws_iam_role_policy_attachment" "backup" {
  count = var.enable_backup ? 1 : 0

  role       = aws_iam_role.backup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# ===========================
