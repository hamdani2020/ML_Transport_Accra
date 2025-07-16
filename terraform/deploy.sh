#!/bin/bash

# ML Transport Accra - Automated Deployment Script
# This script automates the deployment of the ML Transport Accra infrastructure using Terraform

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="ml-transport-accra"
DEFAULT_REGION="us-east-1"
DEFAULT_ENVIRONMENT="dev"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
ML Transport Accra - Terraform Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    init        Initialize Terraform backend and download providers
    plan        Create an execution plan
    apply       Build or change infrastructure
    destroy     Destroy Terraform-managed infrastructure
    output      Show output values
    validate    Validate the configuration files
    format      Format configuration files
    status      Show current deployment status

Options:
    -e, --environment ENV    Environment to deploy (dev, staging, prod) [default: dev]
    -r, --region REGION      AWS region [default: us-east-1]
    -v, --var-file FILE      Path to variables file
    -a, --auto-approve       Skip interactive approval of plan
    -b, --backend-config     Configure backend bucket and DynamoDB table
    -h, --help              Show this help message

Examples:
    $0 init                                    # Initialize Terraform
    $0 -e dev apply                           # Deploy to development (public subnets)
    $0 -e prod -a apply                       # Deploy to production with auto-approve
    $0 plan                                   # Show deployment plan
    $0 destroy                                # Destroy infrastructure
    $0 --backend-config                       # Set up backend resources

Environment Variables:
    AWS_PROFILE             AWS profile to use
    AWS_REGION              AWS region (overrides -r option)
    TF_VAR_*               Terraform variables
    TF_LOG                 Terraform log level (TRACE, DEBUG, INFO, WARN, ERROR)

Prerequisites:
    - AWS CLI configured with appropriate permissions
    - Terraform >= 1.5.0 installed
    - jq installed (for JSON processing)

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install Terraform >= 1.5.0"
        exit 1
    fi

    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    log_info "Found Terraform version: $tf_version"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install AWS CLI v2"
        exit 1
    fi

    local aws_version=$(aws --version | cut -d/ -f2 | cut -d' ' -f1)
    log_info "Found AWS CLI version: $aws_version"

    # Check jq
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. Installing jq for JSON processing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        else
            log_error "Cannot install jq automatically. Please install jq manually."
            exit 1
        fi
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' or set AWS environment variables"
        exit 1
    fi

    local aws_identity=$(aws sts get-caller-identity)
    local aws_account=$(echo $aws_identity | jq -r '.Account')
    local aws_user=$(echo $aws_identity | jq -r '.Arn' | cut -d/ -f2)
    log_info "AWS Account: $aws_account, User: $aws_user"

    log_success "All prerequisites satisfied"
}

# Set up backend resources
setup_backend() {
    log_info "Setting up Terraform backend resources..."

    local bucket_name="${PROJECT_NAME}-terraform-state"
    local dynamodb_table="${PROJECT_NAME}-terraform-locks"
    local region=${AWS_REGION:-$DEFAULT_REGION}

    # Create S3 bucket for state
    log_info "Creating S3 bucket: $bucket_name"
    if aws s3api head-bucket --bucket "$bucket_name" 2>/dev/null; then
        log_warning "S3 bucket $bucket_name already exists"
    else
        aws s3 mb "s3://$bucket_name" --region "$region"
        log_success "Created S3 bucket: $bucket_name"
    fi

    # Enable versioning on bucket
    log_info "Enabling versioning on S3 bucket"
    aws s3api put-bucket-versioning \
        --bucket "$bucket_name" \
        --versioning-configuration Status=Enabled

    # Enable encryption on bucket
    log_info "Enabling encryption on S3 bucket"
    aws s3api put-bucket-encryption \
        --bucket "$bucket_name" \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'

    # Block public access on S3 bucket (instances in public subnets access via IAM roles)
    log_info "Blocking public access on S3 bucket"
    aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration \
            BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

    # Create DynamoDB table for locking
    log_info "Creating DynamoDB table: $dynamodb_table"
    if aws dynamodb describe-table --table-name "$dynamodb_table" 2>/dev/null; then
        log_warning "DynamoDB table $dynamodb_table already exists"
    else
        aws dynamodb create-table \
            --table-name "$dynamodb_table" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region "$region"

        log_info "Waiting for DynamoDB table to be active..."
        aws dynamodb wait table-exists --table-name "$dynamodb_table" --region "$region"
        log_success "Created DynamoDB table: $dynamodb_table"
    fi

    log_success "Backend resources are ready"
    log_info "Backend configured for public subnet architecture:"
    log_info "  bucket = \"$bucket_name\""
    log_info "  dynamodb_table = \"$dynamodb_table\""
    log_info "  region = \"$region\""
}

# Initialize Terraform
terraform_init() {
    log_info "Initializing Terraform..."
    cd "$SCRIPT_DIR"

    # Remove existing .terraform directory if it exists
    if [ -d ".terraform" ]; then
        log_warning "Removing existing .terraform directory"
        rm -rf .terraform
    fi

    terraform init
    log_success "Terraform initialized successfully"
}

# Validate Terraform configuration
terraform_validate() {
    log_info "Validating Terraform configuration..."
    cd "$SCRIPT_DIR"

    terraform validate
    log_success "Terraform configuration is valid"
}

# Format Terraform configuration
terraform_format() {
    log_info "Formatting Terraform configuration..."
    cd "$SCRIPT_DIR"

    terraform fmt -recursive
    log_success "Terraform configuration formatted"
}

# Create Terraform plan
terraform_plan() {
    log_info "Creating Terraform execution plan..."
    cd "$SCRIPT_DIR"

    local var_file_args=""
    if [ -n "$VAR_FILE" ]; then
        var_file_args="-var-file=$VAR_FILE"
    elif [ "$ENVIRONMENT" != "dev" ] && [ -f "environments/${ENVIRONMENT}/terraform.tfvars" ]; then
        var_file_args="-var-file=environments/${ENVIRONMENT}/terraform.tfvars"
    fi

    terraform plan $var_file_args \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=${AWS_REGION:-$DEFAULT_REGION}" \
        -out=tfplan

    log_success "Terraform plan created successfully"
    log_info "Plan saved to: tfplan"
}

# Apply Terraform changes
terraform_apply() {
    log_info "Applying Terraform changes..."
    cd "$SCRIPT_DIR"

    local var_file_args=""
    if [ -n "$VAR_FILE" ]; then
        var_file_args="-var-file=$VAR_FILE"
    elif [ "$ENVIRONMENT" != "dev" ] && [ -f "environments/${ENVIRONMENT}/terraform.tfvars" ]; then
        var_file_args="-var-file=environments/${ENVIRONMENT}/terraform.tfvars"
    fi

    local approve_args=""
    if [ "$AUTO_APPROVE" = "true" ]; then
        approve_args="-auto-approve"
    fi

    # Check if tfplan exists
    if [ -f "tfplan" ]; then
        log_info "Using existing plan file: tfplan"
        terraform apply $approve_args tfplan
        rm -f tfplan
    else
        terraform apply $approve_args $var_file_args \
            -var="environment=$ENVIRONMENT" \
            -var="aws_region=${AWS_REGION:-$DEFAULT_REGION}"
    fi

    log_success "Terraform apply completed successfully"

    # Show important outputs
    log_info "Public subnet deployment completed! Here are the important URLs:"
    terraform output -json | jq -r '
        if .application_url then "Application: " + .application_url.value else empty end,
        if .airflow_url then "Airflow: " + .airflow_url.value else empty end,
        if .mlflow_url then "MLflow: " + .mlflow_url.value else empty end,
        if .dashboard_url then "Dashboard: " + .dashboard_url.value else empty end
    ' 2>/dev/null || log_info "Run 'terraform output' to see deployment details"
    log_info "Note: All instances are in public subnets with security controlled by Security Groups"
}

# Destroy Terraform infrastructure
terraform_destroy() {
    log_warning "This will destroy all Terraform-managed infrastructure!"

    if [ "$AUTO_APPROVE" != "true" ]; then
        read -p "Are you sure you want to destroy the infrastructure? Type 'yes' to confirm: " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "Destroy cancelled"
            exit 0
        fi
    fi

    log_info "Destroying Terraform infrastructure..."
    cd "$SCRIPT_DIR"

    local var_file_args=""
    if [ -n "$VAR_FILE" ]; then
        var_file_args="-var-file=$VAR_FILE"
    elif [ "$ENVIRONMENT" != "dev" ] && [ -f "environments/${ENVIRONMENT}/terraform.tfvars" ]; then
        var_file_args="-var-file=environments/${ENVIRONMENT}/terraform.tfvars"
    fi

    terraform destroy -auto-approve $var_file_args \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=${AWS_REGION:-$DEFAULT_REGION}"

    log_success "Infrastructure destroyed successfully"
}

# Show Terraform outputs
terraform_output() {
    log_info "Terraform outputs:"
    cd "$SCRIPT_DIR"

    terraform output
}

# Show deployment status
show_status() {
    log_info "Deployment Status for Environment: $ENVIRONMENT"
    cd "$SCRIPT_DIR"

    # Check if Terraform is initialized
    if [ ! -d ".terraform" ]; then
        log_warning "Terraform not initialized. Run '$0 init' first."
        return 1
    fi

    # Show workspace
    local workspace=$(terraform workspace show)
    log_info "Terraform Workspace: $workspace"

    # Show state information
    if terraform state list &>/dev/null; then
        local resource_count=$(terraform state list | wc -l)
        log_info "Resources in state: $resource_count"

        # Show outputs if they exist
        if terraform output &>/dev/null; then
            log_info "Key outputs:"
            terraform output -json | jq -r '
                if .application_url then "  Application URL: " + .application_url.value else empty end,
                if .load_balancer_dns_name then "  Load Balancer: " + .load_balancer_dns_name.value else empty end,
                if .vpc_id then "  VPC ID: " + .vpc_id.value else empty end
            ' 2>/dev/null || log_info "  (No outputs available)"
        else
            log_warning "No outputs available"
        fi
    else
        log_warning "No resources found in state"
    fi
}

# Upload application data to S3
upload_data() {
    log_info "Uploading application data to S3..."

    # Get bucket name from Terraform output
    local data_bucket=$(terraform output -json 2>/dev/null | jq -r '.s3_data_bucket_name.value // empty')

    if [ -z "$data_bucket" ]; then
        log_error "Cannot determine S3 data bucket name. Make sure infrastructure is deployed."
        exit 1
    fi

    log_info "Using S3 bucket: $data_bucket"

    # Upload GTFS data
    if [ -d "../data/raw" ]; then
        log_info "Uploading GTFS data..."
        aws s3 sync ../data/raw/ "s3://$data_bucket/gtfs/" --exclude "*.log" --exclude ".*"
        log_success "GTFS data uploaded to public subnet accessible S3 bucket"
    else
        log_warning "GTFS data directory not found: ../data/raw"
    fi

    # Upload configuration
    if [ -f "../configs/config.yaml" ]; then
        log_info "Uploading configuration..."
        aws s3 cp ../configs/config.yaml "s3://$data_bucket/config/config.yaml"
        log_success "Configuration uploaded"
    else
        log_warning "Configuration file not found: ../configs/config.yaml"
    fi

    # Upload processed data if it exists
    if [ -d "../data/processed" ]; then
        log_info "Uploading processed data..."
        aws s3 sync ../data/processed/ "s3://$data_bucket/processed/" --exclude "*.log" --exclude ".*"
        log_success "Processed data uploaded"
    fi

    log_success "Data upload completed"
}

# Parse command line arguments
ENVIRONMENT="$DEFAULT_ENVIRONMENT"
VAR_FILE=""
AUTO_APPROVE="false"
BACKEND_CONFIG="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -v|--var-file)
            VAR_FILE="$2"
            shift 2
            ;;
        -a|--auto-approve)
            AUTO_APPROVE="true"
            shift
            ;;
        -b|--backend-config)
            BACKEND_CONFIG="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            COMMAND="$1"
            shift
            ;;
    esac
done

# Set AWS region if not already set
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="$DEFAULT_REGION"
fi

# Export AWS region for Terraform
export AWS_REGION

# Main execution
main() {
    log_info "ML Transport Accra Deployment Script"
    log_info "Architecture: Public subnets only (no NAT gateway)"
    log_info "Environment: $ENVIRONMENT"
    log_info "AWS Region: $AWS_REGION"

    # Handle backend configuration first
    if [ "$BACKEND_CONFIG" = "true" ]; then
        check_prerequisites
        setup_backend
        exit 0
    fi

    # Check prerequisites for all other commands
    if [ "$COMMAND" != "help" ]; then
        check_prerequisites
    fi

    case $COMMAND in
        init)
            terraform_init
            ;;
        validate)
            terraform_validate
            ;;
        format|fmt)
            terraform_format
            ;;
        plan)
            terraform_plan
            ;;
        apply)
            terraform_apply
            upload_data
            ;;
        destroy)
            terraform_destroy
            ;;
        output)
            terraform_output
            ;;
        status)
            show_status
            ;;
        upload-data)
            upload_data
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Check if command is provided
if [ -z "$COMMAND" ]; then
    log_error "No command specified"
    usage
    exit 1
fi

# Run main function
main

log_success "Script completed successfully"
