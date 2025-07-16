# Root Terraform Configuration for ML Transport Accra Infrastructure
# This file orchestrates all modules to create the complete infrastructure

locals {
  # Common tags to be applied to all resources
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
    Repository  = "ML_Transport_Accra"
  }

  # Application-specific configurations
  app_name = "ml-transport-accra"

  # Availability zones
  availability_zones = data.aws_availability_zones.available.names
}

# Get available availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Generate random suffix for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

# VPC Module - Creates the networking foundation
module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = local.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  enable_vpn_gateway   = var.enable_vpn_gateway
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = local.common_tags
}

# Security Module - Creates security groups and IAM roles
module "security" {
  source = "./modules/security"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  vpc_cidr            = var.vpc_cidr
  allowed_cidr_blocks = var.allowed_cidr_blocks
  ssh_key_name        = var.ssh_key_name

  tags = local.common_tags
}

# S3 Module - Creates S3 buckets for data storage
module "s3" {
  source = "./modules/s3"

  project_name  = var.project_name
  environment   = var.environment
  random_suffix = random_id.suffix.hex

  # S3 bucket configurations
  enable_versioning             = var.s3_enable_versioning
  enable_server_side_encryption = var.s3_enable_encryption
  lifecycle_expiration_days     = var.s3_lifecycle_expiration_days
  transition_to_ia_days         = var.s3_transition_to_ia_days
  transition_to_glacier_days    = var.s3_transition_to_glacier_days

  # Cross-region replication
  enable_cross_region_replication = var.s3_enable_cross_region_replication
  replication_destination_region  = var.s3_replication_destination_region

  tags = local.common_tags
}

# EC2 Module - Creates the application instances
module "ec2" {
  source = "./modules/ec2"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.public_subnet_ids # Use public subnets for instances

  # Instance configuration
  instance_type    = var.instance_type
  min_size         = var.min_instance_count
  max_size         = var.max_instance_count
  desired_capacity = var.desired_instance_count

  # Security
  security_group_ids   = [module.security.application_security_group_id]
  iam_instance_profile = module.security.ec2_instance_profile_name
  key_name             = var.ssh_key_name

  # Application configuration
  s3_data_bucket_name   = module.s3.data_bucket_name
  s3_models_bucket_name = module.s3.models_bucket_name
  s3_logs_bucket_name   = module.s3.logs_bucket_name

  # Monitoring and health checks (CloudWatch disabled)
  enable_detailed_monitoring = false
  health_check_type          = var.health_check_type
  health_check_grace_period  = var.health_check_grace_period

  # Application-specific settings
  docker_compose_version = var.docker_compose_version
  application_port       = var.application_port
  airflow_port           = var.airflow_port
  mlflow_port            = var.mlflow_port

  tags = local.common_tags

  depends_on = [
    module.vpc,
    module.security,
    module.s3
  ]
}

# Upload GTFS data to S3
resource "aws_s3_object" "gtfs_data" {
  for_each = fileset("${path.root}/../data/raw/", "*.txt")

  bucket = module.s3.data_bucket_name
  key    = "gtfs/${each.value}"
  source = "${path.root}/../data/raw/${each.value}"
  etag   = filemd5("${path.root}/../data/raw/${each.value}")

  tags = merge(local.common_tags, {
    DataType = "GTFS"
    Purpose  = "TransportAnalysis"
  })
}

# Upload application configuration to S3
resource "aws_s3_object" "app_config" {
  bucket = module.s3.data_bucket_name
  key    = "config/config.yaml"
  source = "${path.root}/../configs/config.yaml"
  etag   = filemd5("${path.root}/../configs/config.yaml")

  tags = merge(local.common_tags, {
    DataType = "Configuration"
    Purpose  = "ApplicationConfig"
  })
}

# Create application deployment package
data "archive_file" "app_package" {
  type        = "zip"
  output_path = "${path.root}/app-package.zip"

  source {
    content = templatefile("${path.root}/user-data/install-app.sh", {
      s3_data_bucket   = module.s3.data_bucket_name
      s3_models_bucket = module.s3.models_bucket_name
      s3_logs_bucket   = module.s3.logs_bucket_name
      aws_region       = var.aws_region
      environment      = var.environment
    })
    filename = "install-app.sh"
  }

  source {
    content  = file("${path.root}/../docker-compose.yml")
    filename = "docker-compose.yml"
  }

  source {
    content  = file("${path.root}/../requirements.txt")
    filename = "requirements.txt"
  }
}

# Upload application package to S3
resource "aws_s3_object" "app_package" {
  bucket = module.s3.data_bucket_name
  key    = "deployments/app-package.zip"
  source = data.archive_file.app_package.output_path
  etag   = data.archive_file.app_package.output_md5

  tags = merge(local.common_tags, {
    DataType = "Deployment"
    Purpose  = "ApplicationPackage"
  })
}
