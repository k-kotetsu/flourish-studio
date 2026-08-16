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
    # クロスリージョン推論プロファイル(jp./global.など)はアプリ本体と同じ
    # ap-northeast-1から呼ぶ(11_技術構成8.4「案B」。P0-2で決定)。
    bedrock_region: str = "ap-northeast-1"
    # ユーザーディレクトリとしてのCognito(11_技術構成7.2)。AppStackがAuthStackの
    # UserPoolから配線する。ローカル開発では未設定のままテストのモックで代替する。
    cognito_user_pool_id: str | None = None
    cognito_user_pool_client_id: str | None = None
    # Google連携(P3-3、11_技術構成7.5)。Cognito Hosted DomainのURL組み立てと、
    # コールバックURI・遷移先の組み立てに使う。AppStackが環境変数で渡す。
    cognito_domain_prefix: str | None = None
    public_domain_name: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
