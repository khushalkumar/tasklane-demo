terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
}

provider "aws" {
  alias  = "exports"
  region = "us-east-1"
}

resource "aws_s3_bucket" "backups" {
  bucket = "tasklane-backups"
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire-backups"
    status = "Enabled"

    expiration {
      days = 7
    }
  }
}

resource "aws_s3_bucket" "exports" {
  provider = aws.exports
  bucket   = "tasklane-exports"
}
