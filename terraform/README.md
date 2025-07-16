# 🚌 ML Transport Accra - Terraform Infrastructure

This directory contains Terraform configurations for deploying the ML Transport Accra application infrastructure on AWS. The infrastructure follows best practices with a modular approach, comprehensive security, monitoring, and cost optimization.

## 📋 Table of Contents

- [🏗️ Architecture Overview](#️-architecture-overview)
- [📁 Directory Structure](#-directory-structure)
- [🔧 Prerequisites](#-prerequisites)
- [🚀 Quick Start](#-quick-start)
- [📖 Detailed Setup](#-detailed-setup)
- [🔄 Infrastructure Modules](#-infrastructure-modules)
- [🌍 Environment Configuration](#-environment-configuration)
- [🔐 Security Features](#-security-features)
- [📊 Monitoring & Logging](#-monitoring--logging)
- [💰 Cost Optimization](#-cost-optimization)
- [🔄 CI/CD Integration](#-cicd-integration)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📚 Additional Resources](#-additional-resources)

## 🏗️ Architecture Overview

The infrastructure deploys a scalable, secure, and monitored ML application stack:

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     VPC                             │   │
│  │  ┌──────────────┐         ┌──────────────┐         │   │
│  │  │ Public Subnet│         │ Public Subnet│         │   │
│  │  │      AZ-a    │         │      AZ-b    │         │   │
│  │  │              │         │              │         │   │
│  │  │ ┌──────────┐ │         │ ┌──────────┐ │         │   │
│  │  │ │   ALB    │ │         │ │   ALB    │ │         │   │
│  │  │ │          │ │         │ │          │ │         │   │
│  │  │ └──────────┘ │         │ └──────────┘ │         │   │
│  │  │              │         │              │         │   │
│  │  │ ┌──────────┐ │         │ ┌──────────┐ │         │   │
│  │  │ │EC2 Auto  │ │         │ │EC2 Auto  │ │         │   │
│  │  │ │Scaling   │ │         │ │Scaling   │ │         │   │
│  │  │ │Group     │ │         │ │Group     │ │         │   │
│  │  │ └──────────┘ │         │ └──────────┘ │         │   │
│  │  └──────────────┘         └──────────────┘         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   S3 Storage Layer                 │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │   │
│  │  │  Data   │ │ Models  │ │  Logs   │ │Artifacts│  │   │
│  │  │ Bucket  │ │ Bucket  │ │ Bucket  │ │ Bucket  │  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Components:

- **VPC**: Multi-AZ setup with public subnets (simplified architecture)
- **EC2**: Auto Scaling Group with Launch Templates in public subnets
- **ALB**: Application Load Balancer with health checks
- **S3**: Multiple buckets for data, models, logs, and artifacts
- **Security**: IAM roles, Security Groups for network protection
- **Monitoring**: Basic auto-scaling and health checks (CloudWatch disabled for cost savings)
- **Backup**: AWS Backup for data protection

## 📁 Directory Structure

```
terraform/
├── README.md                     # This file
├── main.tf                       # Root module configuration
├── variables.tf                  # Input variables definition
├── outputs.tf                    # Output values definition
├── providers.tf                  # Provider configuration
├── backend.tf                    # Remote state backend
├── terraform.tfvars.example      # Example variables file
├── user-data/
│   └── install-app.sh            # Application installation script
├── environments/
│   └── dev/
│       └── terraform.tfvars      # Development environment config
└── modules/
    ├── vpc/
    │   ├── main.tf               # VPC resources
    │   ├── variables.tf          # VPC variables
    │   └── outputs.tf            # VPC outputs
    ├── security/
    │   ├── main.tf               # Security groups & IAM
    │   ├── variables.tf          # Security variables
    │   └── outputs.tf            # Security outputs
    ├── s3/
    │   ├── main.tf               # S3 buckets
    │   ├── variables.tf          # S3 variables
    │   └── outputs.tf            # S3 outputs
    └── ec2/
        ├── main.tf               # EC2, ASG, ALB
        ├── variables.tf          # EC2 variables
        ├── outputs.tf            # EC2 outputs
        └── user-data.sh          # Instance initialization script
```

## 🔧 Prerequisites

### Required Tools

1. **Terraform** >= 1.5.0
   ```bash
   # Install via Terraform website or package manager
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
   sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
   sudo apt-get update && sudo apt-get install terraform
   ```

2. **AWS CLI** >= 2.0
   ```bash
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

3. **Git**
   ```bash
   sudo apt-get install git
   ```

### AWS Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI configured** with access keys
   ```bash
   aws configure
   ```
3. **S3 Bucket** for Terraform state (see backend setup)
4. **DynamoDB Table** for state locking (see backend setup)
5. **EC2 Key Pair** for SSH access (optional but recommended)

### Required AWS Permissions

Your AWS user/role needs the following permissions:
- EC2: Full access
- VPC: Full access
- S3: Full access
- IAM: Full access
- Application Load Balancer: Full access
- Auto Scaling: Full access
- AWS Backup: Full access (if enabled)

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd ML_Transport_Accra/terraform
```

### 2. Set Up Backend (First Time Only)

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://ml-transport-accra-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ml-transport-accra-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name ml-transport-accra-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

### 3. Configure Variables

```bash
# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your specific values
nano terraform.tfvars
```

### 4. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply infrastructure
terraform apply
```

### 5. Access Your Application

After deployment, Terraform will output the URLs:

```bash
# Get output values
terraform output

# Example outputs:
# application_url = "http://alb-dns-name:8000"
# airflow_url = "http://alb-dns-name:8082"
# mlflow_url = "http://alb-dns-name:5000"
```

## 📖 Detailed Setup

### Step 1: Backend Configuration

The backend configuration is already set up in `backend.tf`. Before first use:

1. **Create the S3 bucket** (if it doesn't exist):
   ```bash
   aws s3 mb s3://ml-transport-accra-terraform-state --region us-east-1
   ```

2. **Create DynamoDB table** for locking:
   ```bash
   aws dynamodb create-table \
     --table-name ml-transport-accra-terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

### Step 2: Configure Variables

1. **Copy the example file**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit key variables**:
   ```hcl
   # Required: Change these values
   project_name = "your-project-name"
   environment  = "dev"  # or "staging", "prod"
   aws_region   = "us-east-1"
   
   # SSH Key (create in AWS Console first)
   ssh_key_name = "your-key-pair-name"
   
   # Email for alerts
   alert_email = "your-email@example.com"
   
   # Instance configuration
   instance_type = "t3.large"  # Adjust based on your needs
   ```

### Step 3: Create SSH Key Pair (Optional)

```bash
# Create key pair in AWS
aws ec2 create-key-pair \
  --key-name ml-transport-dev-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/ml-transport-dev-key.pem

# Set correct permissions
chmod 400 ~/.ssh/ml-transport-dev-key.pem
```

### Step 4: Deploy Infrastructure

```bash
# Validate configuration
terraform validate

# Plan deployment (review changes)
terraform plan

# Apply infrastructure
terraform apply

# Confirm with 'yes' when prompted
```

### Step 5: Upload Application Data

```bash
# Upload GTFS data to S3
aws s3 sync ../data/raw/ s3://your-data-bucket-name/gtfs/

# Upload application configuration
aws s3 cp ../configs/config.yaml s3://your-data-bucket-name/config/
```

## 🔄 Infrastructure Modules

### VPC Module (`modules/vpc/`)

Creates networking foundation:
- **VPC** with DNS support
- **Public Subnets** across multiple AZs (all resources in public subnets)
- **Internet Gateway** for direct internet access
- **Route Tables** and associations
- **VPC Flow Logs** (optional)

**Key Features:**
- Multi-AZ deployment for high availability
- Simplified networking with public subnets only
- Security through Security Groups rather than network isolation
- Cost-effective without NAT gateway charges
- Configurable CIDR blocks
- Optional VPN gateway support

### Security Module (`modules/security/`)

Implements comprehensive security:
- **Security Groups** for network access control
- **IAM Roles and Policies** for AWS service access
- **Key Pair Management** with optional Secrets Manager storage
- **WAF Integration** for application protection

**Key Features:**
- Principle of least privilege
- Automated key generation and storage
- Granular network access control
- Optional compliance frameworks support

### S3 Module (`modules/s3/`)

Creates storage infrastructure:
- **Data Bucket** for GTFS and processed data
- **Models Bucket** for ML artifacts and models
- **Logs Bucket** for application and system logs
- **Artifacts Bucket** for deployment artifacts

**Key Features:**
- Server-side encryption enabled
- Lifecycle policies for cost optimization
- Versioning for data protection
- Cross-region replication (optional)

### EC2 Module (`modules/ec2/`)

Deploys compute infrastructure:
- **Launch Template** with optimized configuration
- **Auto Scaling Group** for high availability
- **Application Load Balancer** with health checks
- **CloudWatch Monitoring** and alerting

**Key Features:**
- Auto-scaling based on demand
- Health monitoring and replacement
- Automated application deployment
- Comprehensive logging and metrics

## 🌍 Environment Configuration

### Development Environment

Located in `environments/dev/terraform.tfvars`:

```hcl
# Cost-optimized for development
instance_type = "t3.large"
min_instance_count = 1
max_instance_count = 2
enable_spot_instances = true

# Relaxed security for easier access (all in public subnets)
# Development-friendly security (all in public subnets)
allowed_cidr_blocks = ["0.0.0.0/0"]
enable_ssh_access = true

# Simplified networking - no NAT gateway costs
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]

# Reduced backup and CloudWatch disabled for cost savings
enable_backup = false
s3_lifecycle_expiration_days = 90
enable_detailed_monitoring = false
```

### Production Environment

For production, create `environments/prod/terraform.tfvars`:

```hcl
# Production-grade instances
instance_type = "m5.xlarge"
min_instance_count = 2
max_instance_count = 6
enable_spot_instances = false

# Restricted security (Security Groups provide protection)
allowed_cidr_blocks = ["your-office-cidr/24"]
enable_ssh_access = true  # Still available as instances are in public subnets

# Full backup and longer retention
enable_backup = true
log_retention_days = 30
s3_lifecycle_expiration_days = 365

# SSL and domain
ssl_certificate_arn = "arn:aws:acm:..."
domain_name = "transport.yourdomain.com"
```

### Using Environments

```bash
# Deploy to development
terraform apply -var-file="environments/dev/terraform.tfvars"

# Deploy to production
terraform apply -var-file="environments/prod/terraform.tfvars"
```

## 🔐 Security Features

### Network Security

- **VPC Isolation**: Complete network isolation
- **Security Groups**: Stateful firewall rules for access control
- **Public Subnets**: Simplified architecture with direct internet access
- **Controlled Access**: Security Groups restrict inbound traffic to required ports only

### Access Control

- **IAM Roles**: Service-specific permissions
- **Instance Profiles**: Secure AWS API access
- **Key Management**: Automated SSH key generation
- **Session Manager**: SSH alternative for secure access

### Data Protection

- **Encryption at Rest**: All EBS volumes and S3 buckets encrypted
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Backup Encryption**: Encrypted backups with retention policies
- **Secret Management**: Sensitive data stored in AWS Secrets Manager

### Application Security

- **WAF Protection**: Web application firewall (optional)
- **Rate Limiting**: API rate limiting and DDoS protection
- **Health Checks**: Automated health monitoring
- **Fail2ban**: Intrusion prevention on instances

## 📊 Monitoring & Logging

### CloudWatch Integration

- **Custom Metrics**: Application-specific metrics
- **Log Aggregation**: Centralized log collection
- **Dashboards**: Visual monitoring interface
- **Alarms**: Automated alerting on thresholds

### Key Metrics Monitored

- **CPU Utilization**: Instance performance
- **Memory Usage**: Memory consumption
- **Disk Space**: Storage utilization
- **Network Traffic**: Bandwidth usage
- **Application Health**: Custom health metrics

### Alerting

- **SNS Notifications**: Email/SMS alerts
- **Auto Scaling Triggers**: Automatic scaling actions
- **Health Check Failures**: Instance replacement
- **Backup Status**: Backup success/failure notifications

### Log Management

- **Application Logs**: FastAPI, Airflow, MLflow logs
- **System Logs**: OS and infrastructure logs
- **Access Logs**: Load balancer access logs
- **Audit Logs**: CloudTrail for API calls (optional)

## 💰 Cost Optimization

### Instance Optimization

- **Spot Instances**: Up to 90% savings for development
- **Right-sizing**: Appropriate instance types per environment
- **Auto Scaling**: Scale down during low usage
- **Scheduled Scaling**: Predictable patterns

### Storage Optimization

- **S3 Lifecycle Policies**: Automatic tier transitions
- **EBS Optimization**: GP3 volumes for better price/performance
- **Log Retention**: Automated old log deletion
- **Data Compression**: Compress stored data

### Network Cost Savings

- **No NAT Gateway**: Eliminates $45/month NAT gateway costs per AZ
- **Public Subnets**: Direct internet access without additional charges
- **Simplified Routing**: Reduced complexity and management overhead

### Monitoring Costs

- **AWS Cost Explorer**: Track spending by service
- **Budget Alerts**: Notification when exceeding budgets
- **Resource Tagging**: Detailed cost allocation
- **Reserved Instances**: For production workloads

### Example Monthly Costs

**Development Environment:**
- t3.large Spot instance: ~$20/month
- Load Balancer: ~$23/month
- S3 Storage (100GB): ~$2/month
- **Total: ~$45/month** (50% savings from no NAT gateway, additional savings from no CloudWatch)

**Production Environment:**
- 2x m5.xlarge instances: ~$280/month
- Load Balancer: ~$23/month
- S3 Storage (1TB): ~$23/month
- Backups: ~$15/month
- **Total: ~$341/month** (15% savings from no NAT gateway, additional savings from no CloudWatch)

## 🔄 CI/CD Integration

### GitHub Actions

Create `.github/workflows/terraform.yml`:

```yaml
name: Terraform

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  terraform:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v1
      with:
        terraform_version: 1.5.0
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Terraform Init
      run: terraform init
      working-directory: ./terraform
    
    - name: Terraform Plan
      run: terraform plan
      working-directory: ./terraform
    
    - name: Terraform Apply
      if: github.ref == 'refs/heads/main'
      run: terraform apply -auto-approve
      working-directory: ./terraform
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - validate
  - plan
  - apply

variables:
  TF_ROOT: terraform
  TF_ADDRESS: ${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/terraform/state/production

terraform:validate:
  stage: validate
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform validate

terraform:plan:
  stage: plan
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform plan

terraform:apply:
  stage: apply
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform apply -auto-approve
  only:
    - main
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Backend Initialization Fails

**Error**: `Error loading backend: bucket does not exist`

**Solution**:
```bash
# Create the backend bucket
aws s3 mb s3://ml-transport-accra-terraform-state
terraform init
```

#### 2. Insufficient IAM Permissions

**Error**: `User is not authorized to perform: ec2:CreateVpc`

**Solution**: Ensure your AWS user has the required permissions or use an admin role.

#### 3. SSH Key Not Found

**Error**: `InvalidKeyPair.NotFound`

**Solution**:
```bash
# Create the key pair first
aws ec2 create-key-pair --key-name your-key-name
```

#### 4. Instance Launch Failures

**Error**: `InsufficientInstanceCapacity`

**Solution**: Try a different instance type or availability zone:
```hcl
instance_type = "t3.medium"  # Instead of t3.large
```

#### 5. Application Not Accessible

**Check**:
1. Security groups allow traffic on required ports
2. Health checks are passing
3. Load balancer is in active state
4. Application is running on instances

### Debugging Commands

```bash
# Check Terraform state
terraform show

# View specific resource
terraform state show aws_instance.example

# Check outputs
terraform output

# Validate configuration
terraform validate

# Plan with detailed output
terraform plan -detailed-exitcode

# Force unlock if locked
terraform force-unlock <lock-id>
```

### Log Locations

- **Terraform logs**: Set `TF_LOG=DEBUG`
- **Instance logs**: `/var/log/user-data.log`
- **Application logs**: `/home/ubuntu/ml-transport-accra/logs/`
- **CloudWatch logs**: AWS Console → CloudWatch → Log Groups

### Health Check Script

The deployment includes a health check script on each instance:

```bash
# SSH to instance and run
sudo -u ubuntu /home/ubuntu/health-check.sh
```

## 📚 Additional Resources

### Documentation

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [AWS Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [AWS Auto Scaling](https://docs.aws.amazon.com/autoscaling/)

### Best Practices

- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)

### Terraform Commands Reference

```bash
# Initialize and download providers
terraform init

# Validate configuration syntax
terraform validate

# Format configuration files
terraform fmt

# Plan changes (dry run)
terraform plan

# Apply changes
terraform apply

# Show current state
terraform show

# List resources in state
terraform state list

# Import existing resource
terraform import <resource_type>.<name> <resource_id>

# Destroy infrastructure
terraform destroy

# Target specific resource
terraform apply -target=<resource>

# Use specific var file
terraform apply -var-file="dev.tfvars"

# Set variable via command line
terraform apply -var="instance_type=t3.medium"

# Deploy with public subnets only (default)
terraform apply -var="public_subnet_cidrs=[\"10.0.1.0/24\",\"10.0.2.0/24\"]"
```

### Support and Contributions

- **Issues**: Report issues in the GitHub repository
- **Contributions**: Submit pull requests for improvements
- **Documentation**: Help improve this documentation

### Version Information

- **Terraform Version**: >= 1.5.0
- **AWS Provider Version**: ~> 5.0
- **Tested AWS Regions**: us-east-1, us-west-2, eu-west-1

---

## 🎯 Quick Reference

### Essential Commands

```bash
# First time setup
terraform init
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform plan
terraform apply

# Updates
terraform plan
terraform apply

# Cleanup
terraform destroy
```

### Important Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `project_name` | Yes | Name of your project |
| `environment` | Yes | Environment (dev/staging/prod) |
| `aws_region` | Yes | AWS region to deploy to |
| `public_subnet_cidrs` | Yes | CIDR blocks for public subnets |
| `ssh_key_name` | No | EC2 key pair for SSH access |
| `alert_email` | No | Email for SNS alerts (CloudWatch disabled) |
| `instance_type` | No | EC2 instance size |

### Default Ports

- **Application**: 8000
- **Airflow**: 8082
- **MLflow**: 5000
- **SSH**: 22 (if enabled)

---

**Happy Terraforming! 🚀**

For questions or support, please refer to the project documentation or create an issue in the repository.