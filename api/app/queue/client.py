from functools import lru_cache

import boto3
from mypy_boto3_sqs.client import SQSClient

from app.core.config import get_settings


@lru_cache
def get_sqs_client() -> SQSClient:
    settings = get_settings()
    return boto3.client("sqs", region_name=settings.aws_region)
