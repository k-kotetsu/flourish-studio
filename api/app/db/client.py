from functools import lru_cache

import boto3
from mypy_boto3_dynamodb.service_resource import Table

from app.core.config import get_settings


@lru_cache
def get_table() -> Table:
    settings = get_settings()
    resource = boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )
    return resource.Table(settings.dynamodb_table_name)
