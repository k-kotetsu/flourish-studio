"""DynamoDB Local専用。テーブルが存在しなければ作成する(技術構成13.1)。

本番のテーブル定義はinfra/lib/data-stack.tsが真実の源であり、ここはローカル開発の
利便のためだけに存在する。
"""

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings


def ensure_table_exists() -> None:
    settings = get_settings()
    client = boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )
    try:
        client.describe_table(TableName=settings.dynamodb_table_name)
        return
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=settings.dynamodb_table_name,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=settings.dynamodb_table_name)


if __name__ == "__main__":
    ensure_table_exists()
