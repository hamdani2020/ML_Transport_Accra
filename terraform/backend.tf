# Terraform Backend Configuration
# This file configures the remote backend for state management

terraform {
  backend "s3" {
    # S3 bucket for storing Terraform state
    bucket = "ml-transport-accra-terraform-state"

    # Path to the state file within the bucket
    key = "infrastructure/terraform.tfstate"

    # AWS region where the S3 bucket is located
    region = "us-east-1"

    # DynamoDB table for state locking
    dynamodb_table = "ml-transport-accra-terraform-locks"

    # Enable state file encryption
    encrypt = true

    # Enable versioning for state files
    versioning = true

    # Server-side encryption configuration
    server_side_encryption_configuration {
      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm = "AES256"
        }
      }
    }
  }
}

# Note: Before using this backend configuration, you need to:
# 1. Create the S3 bucket manually or use a separate Terraform configuration
# 2. Create the DynamoDB table for state locking
# 3. Ensure your AWS credentials have appropriate permissions
#
# To create the backend resources manually:
# aws s3 mb s3://ml-transport-accra-terraform-state --region us-east-1
# aws s3api put-bucket-versioning --bucket ml-transport-accra-terraform-state --versioning-configuration Status=Enabled
# aws s3api put-bucket-encryption --bucket ml-transport-accra-terraform-state --server-side-encryption-configuration file://encryption.json
#
# aws dynamodb create-table \
#   --table-name ml-transport-accra-terraform-locks \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
