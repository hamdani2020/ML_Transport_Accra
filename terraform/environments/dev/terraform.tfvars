# Development Environment Configuration for ML Transport Accra
# This file contains development-specific variable values

# ===========================
# General Configuration
# ===========================

project_name = "ml-transport-accra"
environment  = "dev"
aws_region   = "us-east-1"
owner        = "dev-team"
cost_center  = "development"

# ===========================
# VPC and Networking
# ===========================

vpc_cidr            = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
enable_vpn_gateway  = false

# ===========================
# Security Configuration
# ===========================

# Allow access from anywhere for development (restrict for production)
allowed_cidr_blocks = ["0.0.0.0/0"]

# SSH key name (create this in AWS Console first)
ssh_key_name = "ml-transport-dev-key"

# ===========================
# EC2 Instance Configuration
# ===========================

# Smaller instance for development to save costs
instance_type = "t3.large"

# Single instance for development
min_instance_count     = 1
max_instance_count     = 2
desired_instance_count = 1

# Monitoring
enable_detailed_monitoring = true
health_check_type          = "ELB"
health_check_grace_period  = 300

# ===========================
# Application Ports
# ===========================

application_port       = 8000
airflow_port           = 8082
mlflow_port            = 5000
docker_compose_version = "2.20.0"

# ===========================
# S3 Configuration
# ===========================

s3_enable_versioning          = true
s3_enable_encryption          = true
s3_lifecycle_expiration_days  = 90 # Shorter for dev
s3_transition_to_ia_days      = 7  # Faster transition for dev
s3_transition_to_glacier_days = 30 # Faster transition for dev

# Disable cross-region replication for development
s3_enable_cross_region_replication = false

# ===========================
# Load Balancer & SSL
# ===========================

enable_load_balancer = true

# No SSL for development
ssl_certificate_arn = ""
domain_name         = ""

# ===========================
# Database Configuration
# ===========================

# Use SQLite for development (disable RDS)
enable_rds = false

# ===========================
# Monitoring & Logging (CloudWatch Disabled)
# ===========================

# CloudWatch logs disabled to reduce costs - using local logging and S3 sync
enable_sns_alerts = true
alert_email       = "dev-team@example.com"

# ===========================
# Backup Configuration
# ===========================

# Minimal backups for development
enable_backup         = false
backup_schedule       = "cron(0 6 * * ? *)" # Daily at 6 AM
backup_retention_days = 7

# ===========================
# Cost Optimization
# ===========================

# Use Spot instances for development to save costs
enable_spot_instances = true
spot_instance_types   = ["t3.large", "t3.xlarge", "m5.large"]
spot_max_price        = "0.08"

# ===========================
# Access Control
# ===========================

enable_ssh_access    = true
enable_public_access = true
create_bastion_host  = false

# ===========================
# Development-specific Settings
# ===========================

# Enable development access patterns
development_access = true

# Disable production hardening for easier debugging
production_hardening = false

# ===========================
# Environment Tags
# ===========================

# Additional tags will be merged with default tags
# No need to specify common tags here as they're handled in the root module
