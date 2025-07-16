# 🚌 ML Transport Accra - Complete Deployment Guide

This guide provides a comprehensive overview of deploying the ML Transport Accra application infrastructure using Terraform on AWS, following enterprise-grade best practices.

## 📋 Overview

The ML Transport Accra project is an AI-powered system for analyzing and optimizing public transport routes in Accra, Ghana. This deployment creates a production-ready, scalable infrastructure that includes:

- **Simplified Modular Infrastructure** with VPC (public subnets only), EC2, S3, and Security components
- **Cost-Optimized Architecture** - No NAT gateway costs, CloudWatch disabled, all resources in public subnets
- **Auto-scaling Application Deployment** with Load Balancers and Health Monitoring
- **Security via Security Groups** - Network protection through stateful firewall rules
- **Cost Optimization** with Spot instances, no NAT gateway, no CloudWatch, and lifecycle policies
- **Local Logging & S3 Sync** - Cost-effective logging without CloudWatch charges

## 🏗️ Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet Gateway                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────────────────┐
│                    Public Subnets                          │
│              (Multi-AZ Deployment)                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Application Load Balancer                │   │
│  │           (Ports: 8000, 8082, 5000)                │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Auto Scaling Group                     │   │
│  │  ┌─────────────────┐         ┌─────────────────┐   │   │
│  │  │   EC2 Instance  │   ...   │   EC2 Instance  │   │   │
│  │  │  - FastAPI App  │         │  - FastAPI App  │   │   │
│  │  │  - Airflow      │         │  - Airflow      │   │   │
│  │  │  - MLflow       │         │  - MLflow       │   │   │
│  │  │  - Docker       │         │  - Docker       │   │   │
│  │  └─────────────────┘         └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────────────────────┐
│                   S3 Storage Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │   Data   │ │  Models  │ │   Logs   │ │Artifacts │     │
│  │  Bucket  │ │  Bucket  │ │  Bucket  │ │  Bucket  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Prerequisites

### 1. Required Software

```bash
# Terraform >= 1.5.0
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# AWS CLI >= 2.0
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# jq for JSON processing
sudo apt-get install jq
```

### 2. AWS Setup

```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

### 3. Required Permissions

Your AWS user needs these permissions:
- **EC2**: Full access (instances, security groups, key pairs)
- **VPC**: Full access (VPC, subnets, route tables, gateways)
- **S3**: Full access (buckets, objects, lifecycle policies)
- **IAM**: Full access (roles, policies, instance profiles)
- **CloudWatch**: Full access (logs, metrics, alarms)
- **Application Load Balancer**: Full access
- **Auto Scaling**: Full access
- **AWS Backup**: Full access (if enabled)

## 🚀 Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd ML_Transport_Accra/terraform

# Set up backend resources (first time only)
./deploy.sh --backend-config

# Deploy development environment
./deploy.sh -e dev apply

# Deploy production environment
./deploy.sh -e prod apply
```

### Option 2: Manual Terraform

```bash
cd ML_Transport_Accra/terraform

# Initialize Terraform
terraform init

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Deploy
terraform plan
terraform apply
```

## 📁 Project Structure

```
terraform/
├── 📄 README.md                     # Detailed Terraform documentation
├── 📄 deploy.sh                     # Automated deployment script
├── 📄 main.tf                       # Root module orchestration
├── 📄 variables.tf                  # Input variables
├── 📄 outputs.tf                    # Output values
├── 📄 providers.tf                  # Provider configuration
├── 📄 backend.tf                    # Remote state backend
├── 📄 terraform.tfvars.example      # Example variables
├── 📁 modules/
│   ├── 📁 vpc/                      # VPC, subnets, gateways
│   ├── 📁 security/                 # Security groups, IAM roles
│   ├── 📁 s3/                       # S3 buckets with lifecycle
│   └── 📁 ec2/                      # EC2, ASG, ALB, monitoring
├── 📁 environments/
│   └── 📁 dev/
│       └── 📄 terraform.tfvars      # Environment-specific config
└── 📁 user-data/
    └── 📄 install-app.sh            # Application setup script
```

## 🌍 Environment Configuration

### Development Environment

```hcl
# terraform/environments/dev/terraform.tfvars
project_name = "ml-transport-accra"
environment = "dev"
aws_region = "us-east-1"

# Cost-optimized settings
instance_type = "t3.large"
min_instance_count = 1
max_instance_count = 2
enable_spot_instances = true

# Development-friendly security
allowed_cidr_blocks = ["0.0.0.0/0"]
enable_ssh_access = true

# Reduced retention for cost savings
log_retention_days = 7
s3_lifecycle_expiration_days = 90
enable_backup = false
```

### Production Environment

```hcl
# terraform/environments/prod/terraform.tfvars
project_name = "ml-transport-accra"
environment = "prod"
aws_region = "us-east-1"

# Production-grade settings
instance_type = "m5.xlarge"
min_instance_count = 2
max_instance_count = 6
enable_spot_instances = false

# Restricted security
allowed_cidr_blocks = ["your-office-cidr/24"]
create_bastion_host = true

# Full backup and monitoring
enable_backup = true
log_retention_days = 30
s3_lifecycle_expiration_days = 365
enable_detailed_monitoring = true

# SSL and domain
ssl_certificate_arn = "arn:aws:acm:..."
domain_name = "transport.yourdomain.com"
```

## 🔐 Security Features

### Network Security
- **VPC Isolation**: Complete network separation from other VPCs
- **Multi-AZ Deployment**: High availability across availability zones
- **Public Subnets**: Simplified architecture with direct internet access
- **Security Groups**: Stateful firewall rules controlling all network access
- **Controlled Access**: Inbound traffic restricted to required ports only

### Access Control
- **IAM Roles**: Principle of least privilege
- **Instance Profiles**: Secure AWS API access
- **Key Management**: Automated SSH key generation and storage
- **Session Manager**: Alternative to SSH for secure access

### Data Protection
- **Encryption at Rest**: All EBS volumes and S3 buckets
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Backup Encryption**: Encrypted backups with retention
- **Secret Management**: AWS Secrets Manager integration

### Application Security
- **WAF Protection**: Web application firewall (optional)
- **Rate Limiting**: API rate limiting and DDoS protection
- **Health Monitoring**: Automated health checks
- **Intrusion Prevention**: fail2ban on instances

## 📊 Monitoring & Alerting

### Local Monitoring & Logging
- **Local Log Files**: Application logs stored on instances and synced to S3
- **Health Check Scripts**: Custom health monitoring scripts
- **S3 Log Sync**: Automated log upload to S3 buckets
- **Basic Auto Scaling**: CPU-based target tracking scaling

### Automated Features
- **SNS Notifications**: Email/SMS alerts for critical events
- **Auto Scaling**: CPU-based automatic scaling
- **Health Check Failures**: ALB health checks and instance replacement
- **Log Rotation**: Automated local log cleanup

### Key Monitoring Points
- **Application Health**: Load balancer health checks
- **Auto Scaling**: CPU-based scaling at 70% utilization
- **Log Management**: Local storage with S3 backup
- **Instance Health**: Basic EC2 health monitoring

## 💰 Cost Optimization

### Instance Optimization
- **Spot Instances**: Up to 90% savings for development
- **Right-sizing**: Appropriate instance types per environment
- **Auto Scaling**: Scale down during low usage
- **Scheduled Scaling**: Predictable patterns

### Storage Optimization
- **S3 Lifecycle Policies**: Automatic tier transitions
  - Standard → IA (30 days)
  - IA → Glacier (90 days)
  - Delete old data (365 days)
- **EBS Optimization**: GP3 volumes for better price/performance
- **Log Retention**: Automated cleanup

### Estimated Monthly Costs

**Development:**
- t3.large Spot instance: ~$20
- Load Balancer: ~$23
- NAT Gateway: ~$45
- S3 Storage (100GB): ~$2
- **Total: ~$90/month**

**Production:**
- 2x m5.xlarge instances: ~$280
- Load Balancer: ~$23
- NAT Gateway: ~$45
- S3 Storage (1TB): ~$23
- Backups: ~$15
- **Total: ~$386/month**

## 🔄 Deployment Steps

### 1. Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd ML_Transport_Accra/terraform

# Set up backend (first time only)
./deploy.sh --backend-config
```

### 2. Configure Variables

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars

# Required changes:
# - ssh_key_name: Your AWS key pair name
# - alert_email: Your email for notifications
# - allowed_cidr_blocks: Your IP range for security (important for public subnets)
# - public_subnet_cidrs: CIDR blocks for your public subnets
```

### 3. Deploy Infrastructure

```bash
# Development deployment
./deploy.sh -e dev apply

# Production deployment
./deploy.sh -e prod apply

# With auto-approve for CI/CD
./deploy.sh -e prod -a apply
```

### 4. Verify Deployment

```bash
# Check deployment status
./deploy.sh status

# View outputs
terraform output

# Test applications
curl http://<load-balancer-dns>:8000/health
```

## 🛠️ Management Commands

### Deployment Script Usage

```bash
# Available commands
./deploy.sh init                    # Initialize Terraform
./deploy.sh plan                    # Show deployment plan
./deploy.sh apply                   # Deploy infrastructure
./deploy.sh destroy                 # Destroy infrastructure
./deploy.sh status                  # Show current status
./deploy.sh upload-data             # Upload GTFS data to S3

# Options
./deploy.sh -e prod apply           # Deploy to production
./deploy.sh -a apply                # Auto-approve without prompt
./deploy.sh --backend-config        # Set up backend resources
```

### Direct Terraform Commands

```bash
# Standard Terraform workflow
terraform init
terraform validate
terraform plan
terraform apply
terraform destroy

# Environment-specific deployment
terraform apply -var-file="environments/prod/terraform.tfvars"

# Target specific resources
terraform apply -target=module.vpc
```

## 🚨 Troubleshooting

### Common Issues

**1. Backend Initialization Fails**
```bash
# Create backend bucket first
aws s3 mb s3://ml-transport-accra-terraform-state
terraform init
```

**2. Insufficient Permissions**
```bash
# Check current permissions
aws sts get-caller-identity
aws iam get-user
```

**3. SSH Key Not Found**
```bash
# Create key pair
aws ec2 create-key-pair --key-name your-key-name \
  --query 'KeyMaterial' --output text > ~/.ssh/your-key.pem
chmod 400 ~/.ssh/your-key.pem
```

**4. Application Not Accessible**
- Check security groups allow traffic on required ports (critical for public subnet security)
- Verify health checks are passing
- Ensure load balancer is in active state
- Check application logs locally: `/home/ubuntu/ml-transport-accra/logs/`
- Verify instances have public IPs assigned
- Check S3 for uploaded logs: `aws s3 ls s3://your-logs-bucket/logs/`

### Debug Commands

```bash
# Check Terraform state
terraform show
terraform state list

# View specific resource
terraform state show aws_instance.example

# Check logs
# Instance logs: /var/log/user-data.log
# Application logs: /home/ubuntu/ml-transport-accra/logs/
# S3 logs: aws s3 ls s3://your-logs-bucket/logs/
# Health check: /home/ubuntu/health-check.sh
```

## 📱 Application Access

After successful deployment:

### Service URLs
- **Main Application**: `http://<alb-dns>:8000`
- **API Documentation**: `http://<alb-dns>:8000/docs`
- **Dashboard**: `http://<alb-dns>:8000/dashboard`
- **Airflow**: `http://<alb-dns>:8082` (admin/admin)
- **MLflow**: `http://<alb-dns>:5000`

### SSH Access (Direct - Public Subnets)
```bash
# Get instance public IP from AWS Console or:
aws ec2 describe-instances --filters "Name=tag:Project,Values=ml-transport-accra" \
  --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,State.Name]' \
  --output table

# SSH to instance (direct access via public IP)
ssh -i ~/.ssh/your-key.pem ubuntu@<public-instance-ip>

# Run health check
sudo -u ubuntu /home/ubuntu/health-check.sh
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Infrastructure
on:
  push:
    branches: [main]
    paths: ['terraform/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy Infrastructure
        run: |
          cd terraform
          ./deploy.sh -e prod -a apply
```

## 📈 Scaling & Performance

### Horizontal Scaling
- **Auto Scaling Group**: Automatically adjusts instance count in public subnets
- **Load Balancer**: Distributes traffic across instances in multiple AZs
- **Multi-AZ**: Instances spread across availability zones for high availability

### Vertical Scaling
- **Instance Types**: Easily change in terraform.tfvars
- **Storage**: Configurable EBS volume sizes
- **Memory**: Instance type determines available memory

### Performance Monitoring
- **Basic EC2 Metrics**: CPU utilization for auto scaling
- **Application Health**: Load balancer health checks
- **Local Monitoring**: Health check scripts and log analysis
- **Load Balancer Metrics**: Request routing and health status

## 🧹 Cleanup

### Destroy Infrastructure

```bash
# Using deployment script (recommended)
./deploy.sh destroy

# Manual Terraform
terraform destroy

# Force destroy if needed
terraform destroy -auto-approve
```

### Clean Up Backend Resources

```bash
# Delete S3 bucket (careful - this removes state!)
aws s3 rb s3://ml-transport-accra-terraform-state --force

# Delete DynamoDB table
aws dynamodb delete-table --table-name ml-transport-accra-terraform-locks
```

## 📚 Additional Resources

### Documentation
- [Terraform Documentation](https://www.terraform.io/docs)
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

### ML Transport Accra Specific
- [Application Documentation](../README.md)
- [API Documentation](../api/README.md)
- [ML Pipeline Documentation](../docs/ML_PIPELINE.md)

### Support
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Contributing**: See CONTRIBUTING.md for contribution guidelines

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] AWS credentials configured with proper permissions
- [ ] SSH key pair created in AWS Console
- [ ] terraform.tfvars configured with production values
- [ ] Backend S3 bucket and DynamoDB table created
- [ ] SSL certificate obtained (for HTTPS)
- [ ] Domain name configured (optional)
- [ ] Alert email configured
- [ ] Security groups properly configured (critical for public subnet security)
- [ ] SSH access restricted to trusted IP ranges
- [ ] Backup strategy configured
- [ ] Basic monitoring and health checks tested
- [ ] Cost budgets and alerts set up
- [ ] Network access controls validated
- [ ] Documentation updated for your specific deployment

**Happy Deploying! 🚀**

This infrastructure provides a robust, scalable, and highly cost-effective foundation for the ML Transport Accra application. The simplified public subnet architecture with CloudWatch disabled significantly reduces costs while maintaining security through properly configured Security Groups and local monitoring. The modular Terraform approach ensures maintainability and allows for easy customization as your requirements evolve.