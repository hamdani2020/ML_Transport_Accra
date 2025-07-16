# Security Module - Main Configuration
# Creates security groups, IAM roles, and policies for the ML Transport Accra infrastructure
# Note: All resources are deployed in public subnets with security controlled via Security Groups

locals {
  # Common tags for all security resources
  security_tags = merge(var.tags, {
    Component = "security"
    Module    = "security"
  })
}

# ===========================
# Security Groups
# ===========================

# Application Security Group - For EC2 instances running the ML application
resource "aws_security_group" "application" {
  name        = "${var.project_name}-${var.environment}-application-sg"
  description = "Security group for ML Transport Accra application instances"
  vpc_id      = var.vpc_id

  # HTTP access for FastAPI application
  ingress {
    description = "HTTP for FastAPI application"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Airflow web interface
  ingress {
    description = "Airflow web interface"
    from_port   = 8082
    to_port     = 8082
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # MLflow web interface
  ingress {
    description = "MLflow web interface"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # SSH access (conditional)
  dynamic "ingress" {
    for_each = var.enable_ssh_access ? [1] : []
    content {
      description = "SSH access"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.ssh_allowed_cidrs
    }
  }

  # HTTPS access
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Health check from ALB
  ingress {
    description     = "Health check from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow inter-instance communication on application ports
  ingress {
    description = "Inter-instance communication"
    from_port   = 5000
    to_port     = 8082
    protocol    = "tcp"
    self        = true
  }

  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-application-sg"
    Type = "application"
  })
}

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # HTTP access
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # HTTPS access
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Custom application ports
  ingress {
    description = "Application port 8000"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  ingress {
    description = "Airflow port 8082"
    from_port   = 8082
    to_port     = 8082
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  ingress {
    description = "MLflow port 5000"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-alb-sg"
    Type = "load_balancer"
  })
}

# Database Security Group (for RDS if enabled)
# Note: In public subnet architecture, database access is still restricted to application instances
resource "aws_security_group" "database" {
  count = var.enable_database_sg ? 1 : 0

  name        = "${var.project_name}-${var.environment}-database-sg"
  description = "Security group for RDS database (public subnet deployment)"
  vpc_id      = var.vpc_id

  # PostgreSQL access from application instances
  ingress {
    description     = "PostgreSQL from application"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  # No outbound rules needed for RDS

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-database-sg"
    Type = "database"
  })
}

# Bastion Host Security Group (optional)
# Note: With public subnet architecture, bastion may be less necessary but still available
resource "aws_security_group" "bastion" {
  count = var.enable_bastion_sg ? 1 : 0

  name        = "${var.project_name}-${var.environment}-bastion-sg"
  description = "Security group for bastion host (public subnet deployment)"
  vpc_id      = var.vpc_id

  # SSH access
  ingress {
    description = "SSH access to bastion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.bastion_allowed_cidrs
  }

  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-bastion-sg"
    Type = "bastion"
  })
}

# ===========================
# IAM Roles and Policies
# ===========================

# EC2 Instance Role
resource "aws_iam_role" "ec2_instance_role" {
  name = "${var.project_name}-${var.environment}-ec2-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-ec2-instance-role"
  })
}

# EC2 Instance Profile
resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "${var.project_name}-${var.environment}-ec2-instance-profile"
  role = aws_iam_role.ec2_instance_role.name

  tags = local.security_tags
}

# S3 Access Policy for EC2 instances
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-${var.environment}-s3-access-policy"
  role = aws_iam_role.ec2_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:ListBucketMultipartUploads",
          "s3:ListMultipartUploadParts",
          "s3:AbortMultipartUpload"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-*",
          "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
        ]
      }
    ]
  })
}

# CloudWatch policies removed to reduce costs and complexity

# SSM Policy for Parameter Store and Session Manager
resource "aws_iam_role_policy" "ssm_access" {
  name = "${var.project_name}-${var.environment}-ssm-access-policy"
  role = aws_iam_role.ec2_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
          "ec2messages:AcknowledgeMessage",
          "ec2messages:DeleteMessage",
          "ec2messages:FailMessage",
          "ec2messages:GetEndpoint",
          "ec2messages:GetMessages",
          "ec2messages:SendReply"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECR Access Policy (for Docker images)
resource "aws_iam_role_policy" "ecr_access" {
  count = var.enable_ecr_access ? 1 : 0

  name = "${var.project_name}-${var.environment}-ecr-access-policy"
  role = aws_iam_role.ec2_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# SNS Publish Policy (for notifications)
resource "aws_iam_role_policy" "sns_publish" {
  count = var.enable_sns_access ? 1 : 0

  name = "${var.project_name}-${var.environment}-sns-publish-policy"
  role = aws_iam_role.ec2_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:GetTopicAttributes",
          "sns:ListTopics"
        ]
        Resource = "arn:aws:sns:*:*:${var.project_name}-${var.environment}-*"
      }
    ]
  })
}

# Secrets Manager Access (for sensitive configuration)
resource "aws_iam_role_policy" "secrets_manager" {
  count = var.enable_secrets_manager_access ? 1 : 0

  name = "${var.project_name}-${var.environment}-secrets-manager-policy"
  role = aws_iam_role.ec2_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:${var.project_name}/${var.environment}/*"
      }
    ]
  })
}

# ===========================
# Key Pair (Optional)
# ===========================

# Generate TLS private key
resource "tls_private_key" "ec2_key" {
  count = var.create_key_pair ? 1 : 0

  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS Key Pair
resource "aws_key_pair" "ec2_key" {
  count = var.create_key_pair ? 1 : 0

  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = tls_private_key.ec2_key[0].public_key_openssh

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-key"
  })
}

# Store private key in AWS Secrets Manager
resource "aws_secretsmanager_secret" "ec2_private_key" {
  count = var.create_key_pair && var.store_key_in_secrets_manager ? 1 : 0

  name        = "${var.project_name}/${var.environment}/ec2-private-key"
  description = "Private key for EC2 instances"

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-ec2-private-key"
  })
}

resource "aws_secretsmanager_secret_version" "ec2_private_key" {
  count = var.create_key_pair && var.store_key_in_secrets_manager ? 1 : 0

  secret_id     = aws_secretsmanager_secret.ec2_private_key[0].id
  secret_string = tls_private_key.ec2_key[0].private_key_pem
}

# ===========================
# Security Group Rules for Database Access
# ===========================

# Additional security group rule for database access from specific sources
resource "aws_security_group_rule" "database_access_from_cidr" {
  count = var.enable_database_sg && length(var.database_allowed_cidrs) > 0 ? 1 : 0

  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = var.database_allowed_cidrs
  security_group_id = aws_security_group.database[0].id
  description       = "PostgreSQL access from allowed CIDR blocks"
}

# ===========================
# WAF Web ACL (Optional)
# ===========================

resource "aws_wafv2_web_acl" "main" {
  count = var.enable_waf ? 1 : 0

  name  = "${var.project_name}-${var.environment}-web-acl"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  tags = merge(local.security_tags, {
    Name = "${var.project_name}-${var.environment}-web-acl"
  })

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-${var.environment}-web-acl"
    sampled_requests_enabled   = true
  }
}
