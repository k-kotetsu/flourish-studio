"""flourishテーブルへの汎用アクセス。エンティティ固有のロジックは持たない。

パターンはスキルflourish-data、08_データモデル2章を参照。
"""

from typing import Any, cast

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.type_defs import TransactWriteItemTypeDef

from app.core.config import get_settings
from app.db.client import get_table
from app.db.keys import history_sk

Item = dict[str, Any]
TransactItem = dict[str, Any]

_serializer = TypeSerializer()


class ConditionalCheckFailed(Exception):
    """条件付き書き込み・トランザクションの条件式が満たされなかった。"""


def get_item(pk: str, sk: str) -> Item | None:
    response = get_table().get_item(Key={"PK": pk, "SK": sk})
    return response.get("Item")


def put_item(
    item: Item,
    condition_expression: str | None = None,
    expression_attribute_values: dict[str, Any] | None = None,
) -> None:
    kwargs: dict[str, Any] = {"Item": item}
    if condition_expression is not None:
        kwargs["ConditionExpression"] = condition_expression
    if expression_attribute_values is not None:
        kwargs["ExpressionAttributeValues"] = expression_attribute_values
    try:
        get_table().put_item(**kwargs)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConditionalCheckFailed from error
        raise


def update_item(
    pk: str,
    sk: str,
    update_expression: str,
    expression_attribute_values: dict[str, Any],
    expression_attribute_names: dict[str, str] | None = None,
    condition_expression: str | None = None,
) -> Item:
    kwargs: dict[str, Any] = {
        "Key": {"PK": pk, "SK": sk},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_attribute_values,
        "ReturnValues": "ALL_NEW",
    }
    if expression_attribute_names is not None:
        kwargs["ExpressionAttributeNames"] = expression_attribute_names
    if condition_expression is not None:
        kwargs["ConditionExpression"] = condition_expression
    try:
        response = get_table().update_item(**kwargs)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConditionalCheckFailed from error
        raise
    attributes: Item = response["Attributes"]
    return attributes


def batch_get_items(keys: list[tuple[str, str]]) -> list[Item]:
    if not keys:
        return []
    settings = get_settings()
    resource = boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )
    response = resource.batch_get_item(
        RequestItems={
            settings.dynamodb_table_name: {"Keys": [{"PK": pk, "SK": sk} for pk, sk in keys]},
        },
    )
    items: list[Item] = response["Responses"][settings.dynamodb_table_name]
    return items


def query_by_sk_prefix(
    pk: str,
    sk_prefix: str,
    scan_index_forward: bool = True,
    limit: int | None = None,
) -> list[Item]:
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix),
        "ScanIndexForward": scan_index_forward,
    }
    if limit is not None:
        kwargs["Limit"] = limit
    response = get_table().query(**kwargs)
    items: list[Item] = response["Items"]
    return items


def _serialize_transact_item(item: TransactItem) -> dict[str, Any]:
    action, body = next(iter(item.items()))
    serialized: dict[str, Any] = {"TableName": get_settings().dynamodb_table_name}
    for key, value in body.items():
        if key in ("Item", "Key", "ExpressionAttributeValues"):
            serialized[key] = {k: _serializer.serialize(v) for k, v in value.items()}
        else:
            serialized[key] = value
    return {action: serialized}


def transact_write_items(items: list[TransactItem]) -> None:
    """Put/Update/Delete/ConditionCheckのTransactItemを受け取り実行する。

    各要素はboto3の低レベルAPIと同じ形だが、値はPython nativeのまま渡してよい
    (DynamoDB形式への変換はここで行う)。
    """
    settings = get_settings()
    client = boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )
    try:
        client.transact_write_items(
            TransactItems=cast(
                list[TransactWriteItemTypeDef],
                [_serialize_transact_item(item) for item in items],
            ),
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "TransactionCanceledException":
            raise ConditionalCheckFailed from error
        raise


def put_versioned(pk: str, current_sk: str, history_sk_prefix: str, new_attributes: Item) -> Item:
    """現行版を読み、履歴退避と新版書き込みを1トランザクションで行う。

    条件式(version一致)が同時更新の一方を弾く(スキルflourish-data「更新の型」)。
    新版のitemを返す。
    """
    old = get_item(pk, current_sk)
    version = int(old["version"]) if old is not None else 0
    new_item: Item = {**new_attributes, "PK": pk, "SK": current_sk, "version": version + 1}

    transact_items: list[TransactItem] = []
    if old is not None:
        transact_items.append(
            {"Put": {"Item": {**old, "SK": history_sk(history_sk_prefix, version)}}},
        )
    transact_items.append(
        {
            "Put": {
                "Item": new_item,
                "ConditionExpression": "attribute_not_exists(PK) OR version = :v",
                "ExpressionAttributeValues": {":v": version},
            },
        },
    )
    transact_write_items(transact_items)
    return new_item
