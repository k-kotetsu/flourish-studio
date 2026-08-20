"""content/articles/ 配下のJSONを flourish_article テーブルへ投入する。

記事は管理画面を持たず直接投入する方針（08_データモデル 6.4）。PKは`slug`のため、
`put_item`による上書きだけで冪等性が成り立つ（同じslugの再投入は重複を生まず、
内容の更新として反映される）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict, cast

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb import DynamoDBClient, DynamoDBServiceResource

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "content" / "articles"
# 実AWSでの物理名は`flourish_article-dev`/`flourish_article-prod`(P7-10、
# `infra/lib/data-stack.ts`)。DynamoDB Local(ローカル・テスト)では未設定のまま既定値を使う。
TABLE_NAME = os.environ.get("ARTICLE_TABLE_NAME", "flourish_article")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")


class Article(TypedDict):
    slug: str
    title: str
    excerpt: str
    body: str
    category: str
    reading_minutes: int
    status: str
    published_at: str


def load_articles(directory: Path = ARTICLES_DIR) -> list[Article]:
    return [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))
    ]


def get_client() -> DynamoDBClient:
    return boto3.client(
        "dynamodb", region_name=AWS_REGION, endpoint_url=DYNAMODB_ENDPOINT_URL
    )


def get_resource() -> DynamoDBServiceResource:
    return boto3.resource(
        "dynamodb", region_name=AWS_REGION, endpoint_url=DYNAMODB_ENDPOINT_URL
    )


def ensure_table_exists(client: DynamoDBClient) -> None:
    try:
        client.describe_table(TableName=TABLE_NAME)
        return
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[
            {"AttributeName": "slug", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
            {"AttributeName": "published_at", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "slug", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "category-index",
                "KeySchema": [
                    {"AttributeName": "category", "KeyType": "HASH"},
                    {"AttributeName": "published_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=TABLE_NAME)


def insert_articles(directory: Path = ARTICLES_DIR) -> list[Article]:
    ensure_table_exists(get_client())

    table = get_resource().Table(TABLE_NAME)
    articles = load_articles(directory)
    for article in articles:
        table.put_item(Item=cast(dict[str, Any], article))
    print(f"{len(articles)}件の記事を {TABLE_NAME} に投入しました。")
    return articles


if __name__ == "__main__":
    insert_articles()
