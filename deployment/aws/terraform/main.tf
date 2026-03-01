# Autonomous Field Engineer - AWS Infrastructure
# Terraform configuration for deploying the system to AWS

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for Image Storage
resource "aws_s3_bucket" "field_images" {
  bucket = "${var.project_name}-field-images-${var.environment}"
  
  tags = {
    Name        = "Field Engineer Images"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "field_images" {
  bucket = aws_s3_bucket.field_images.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "field_images" {
  bucket = aws_s3_bucket.field_images.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket for Technical Manuals
resource "aws_s3_bucket" "technical_manuals" {
  bucket = "${var.project_name}-technical-manuals-${var.environment}"
  
  tags = {
    Name        = "Technical Manuals"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "technical_manuals" {
  bucket = aws_s3_bucket.technical_manuals.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# IAM Role for Orchestration Layer
resource "aws_iam_role" "orchestration_role" {
  name = "${var.project_name}-orchestration-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "Orchestration Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for Bedrock Access
resource "aws_iam_policy" "bedrock_access" {
  name        = "${var.project_name}-bedrock-access-${var.environment}"
  description = "Allow access to Amazon Bedrock models"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
        ]
      }
    ]
  })
}

# IAM Policy for S3 Access
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access-${var.environment}"
  description = "Allow access to S3 buckets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.field_images.arn,
          "${aws_s3_bucket.field_images.arn}/*",
          aws_s3_bucket.technical_manuals.arn,
          "${aws_s3_bucket.technical_manuals.arn}/*"
        ]
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.orchestration_role.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.orchestration_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "orchestration" {
  name              = "/aws/afe/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name        = "Orchestration Logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway (optional - for REST API exposure)
resource "aws_apigatewayv2_api" "orchestration_api" {
  count         = var.enable_api_gateway ? 1 : 0
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
  
  tags = {
    Name        = "Orchestration API"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Outputs
output "field_images_bucket" {
  description = "S3 bucket for field images"
  value       = aws_s3_bucket.field_images.id
}

output "technical_manuals_bucket" {
  description = "S3 bucket for technical manuals"
  value       = aws_s3_bucket.technical_manuals.id
}

output "orchestration_role_arn" {
  description = "IAM role ARN for orchestration layer"
  value       = aws_iam_role.orchestration_role.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.orchestration.name
}
