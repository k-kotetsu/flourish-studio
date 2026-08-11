from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: Literal["local", "dev", "prod"] = "local"
    aws_region: str = "ap-northeast-1"
    dynamodb_table_name: str = "flourish"
    # ローカル(DynamoDB Local)を指す。本番はNoneのままAWSのデフォルトエンドポイントを使う。
    dynamodb_endpoint_url: str | None = None
    # 非同期ジョブのSQSキューURL(11_技術構成5.5)。Lambda環境変数から渡す。
    job_queue_url: str | None = None
    # Bedrockのみus-east-1で呼ぶ。アプリ本体(aws_region)とは別リージョン
    # (11_技術構成8.4。東京はSonnet 5のIn-Region推論に非対応)。
    bedrock_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
