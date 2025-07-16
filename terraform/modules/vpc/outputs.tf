# VPC Module Outputs
# This file defines all output values from the VPC module

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_instance_tenancy" {
  description = "Tenancy of instances spin up within VPC"
  value       = aws_vpc.main.instance_tenancy
}

output "vpc_enable_dns_support" {
  description = "Whether or not the VPC has DNS support"
  value       = aws_vpc.main.enable_dns_support
}

output "vpc_enable_dns_hostnames" {
  description = "Whether or not the VPC has DNS hostname support"
  value       = aws_vpc.main.enable_dns_hostnames
}

output "vpc_main_route_table_id" {
  description = "ID of the main route table associated with this VPC"
  value       = aws_vpc.main.main_route_table_id
}

output "vpc_default_network_acl_id" {
  description = "ID of the default network ACL"
  value       = aws_vpc.main.default_network_acl_id
}

output "vpc_default_security_group_id" {
  description = "ID of the security group created by default on VPC creation"
  value       = aws_vpc.main.default_security_group_id
}

output "vpc_default_route_table_id" {
  description = "ID of the default route table"
  value       = aws_vpc.main.default_route_table_id
}

# Internet Gateway
output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "internet_gateway_arn" {
  description = "ARN of the Internet Gateway"
  value       = aws_internet_gateway.main.arn
}

# Public Subnets
output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "public_subnet_arns" {
  description = "ARNs of the public subnets"
  value       = aws_subnet.public[*].arn
}

output "public_subnet_cidr_blocks" {
  description = "CIDR blocks of the public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "public_subnet_availability_zones" {
  description = "Availability zones of the public subnets"
  value       = aws_subnet.public[*].availability_zone
}

# For compatibility - return empty values for private subnets
output "private_subnet_ids" {
  description = "IDs of the private subnets (empty - all subnets are public)"
  value       = []
}

output "private_subnet_arns" {
  description = "ARNs of the private subnets (empty - all subnets are public)"
  value       = []
}

output "private_subnet_cidr_blocks" {
  description = "CIDR blocks of the private subnets (empty - all subnets are public)"
  value       = []
}

output "private_subnet_availability_zones" {
  description = "Availability zones of the private subnets (empty - all subnets are public)"
  value       = []
}

# NAT Gateways - disabled (all resources in public subnets)
output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

output "nat_gateway_public_ips" {
  description = "Public IPs of the NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

output "nat_gateway_private_ips" {
  description = "Private IPs of the NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

# Elastic IPs
output "eip_ids" {
  description = "IDs of the Elastic IPs for NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

output "eip_allocation_ids" {
  description = "Allocation IDs of the Elastic IPs for NAT Gateways (empty - NAT gateways not used)"
  value       = []
}

# Route Tables
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of the private route tables (empty - all subnets use public route table)"
  value       = []
}

output "public_route_table_association_ids" {
  description = "IDs of the associations between public subnets and public route table"
  value       = aws_route_table_association.public[*].id
}

output "private_route_table_association_ids" {
  description = "IDs of the associations between private subnets and private route tables (empty)"
  value       = []
}

# VPN Gateway
output "vpn_gateway_id" {
  description = "ID of the VPN Gateway"
  value       = var.enable_vpn_gateway ? aws_vpn_gateway.main[0].id : null
}

output "vpn_gateway_arn" {
  description = "ARN of the VPN Gateway"
  value       = var.enable_vpn_gateway ? aws_vpn_gateway.main[0].arn : null
}

# DHCP Options
output "dhcp_options_id" {
  description = "ID of the DHCP Options Set"
  value       = aws_vpc_dhcp_options.main.id
}

output "dhcp_options_association_id" {
  description = "ID of the DHCP Options Set Association"
  value       = aws_vpc_dhcp_options_association.main.id
}

# Flow Logs
output "vpc_flow_log_id" {
  description = "ID of the VPC Flow Log"
  value       = var.enable_flow_logs ? aws_flow_log.vpc[0].id : null
}

output "vpc_flow_log_cloudwatch_log_group_name" {
  description = "Name of the CloudWatch Log Group for VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.vpc_flow_log[0].name : null
}

# Network ACL
output "network_acl_id" {
  description = "ID of the Network ACL"
  value       = var.enable_network_acl ? aws_network_acl.main[0].id : null
}

# Summary information
output "availability_zones" {
  description = "List of availability zones used"
  value       = slice(var.availability_zones, 0, local.az_count)
}

output "subnet_count" {
  description = "Number of subnets created per type"
  value = {
    public  = length(aws_subnet.public)
    private = 0
    total   = length(aws_subnet.public)
  }
}

output "vpc_endpoints" {
  description = "Information about VPC endpoints (if any are created in the future)"
  value       = {}
}
