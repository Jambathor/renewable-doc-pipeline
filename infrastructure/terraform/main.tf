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

locals {
  app_name = "renewable-doc-pipeline"
  environment = var.environment
  
  common_tags = {
    Project     = local.app_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "app_runner_instance_config" {
  description = "App Runner instance configuration"
  type = object({
    cpu    = string
    memory = string
  })
  default = {
    cpu    = "0.25 vCPU"
    memory = "0.5 GB"
  }
}

# S3 Bucket for document storage
resource "aws_s3_bucket" "documents" {
  bucket = "${local.app_name}-documents-${local.environment}-${random_id.bucket_suffix.hex}"
  tags   = local.common_tags
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ECR Repository
resource "aws_ecr_repository" "api" {
  name                 = "${local.app_name}-api"
  image_tag_mutability = "MUTABLE"
  tags                 = local.common_tags

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for App Runner
resource "aws_iam_role" "app_runner_instance" {
  name = "${local.app_name}-app-runner-instance-${local.environment}"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "app_runner_s3_access" {
  name = "${local.app_name}-s3-access"
  role = aws_iam_role.app_runner_instance.id

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
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

# App Runner Service
resource "aws_apprunner_service" "api" {
  service_name = "${local.app_name}-api-${local.environment}"
  tags         = local.common_tags

  source_configuration {
    image_repository {
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          AWS_DEFAULT_REGION = var.aws_region
          S3_BUCKET_NAME     = aws_s3_bucket.documents.bucket
          STORAGE_BACKEND    = "s3"
          ENVIRONMENT        = local.environment
        }
      }
      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
    }
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu               = var.app_runner_instance_config.cpu
    memory            = var.app_runner_instance_config.memory
    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  health_check_configuration {
    healthy_threshold   = 1
    interval            = 10
    path                = "/healthz"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 5
  }
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for document storage"
  value       = aws_s3_bucket.documents.bucket
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = "https://${aws_apprunner_service.api.service_url}"
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.api.arn
}