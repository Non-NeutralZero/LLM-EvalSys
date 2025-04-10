#!/usr/bin/env python3
import os

DEFAULT_S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "your-s3-bucket-name")

BEDROCK_DEFAULT_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"
BEDROCK_FALLBACK_MODEL = "anthropic.claude-instant-v1"

# Generation Lambda function name
DEFAULT_LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "YOUR_LAMBDA_FUNCTION_NAME")

DEFAULT_MAX_WORKERS = 5

TMP_DIR = "./.tmp"
os.makedirs(TMP_DIR, exist_ok=True) 