"""Bedrockクライアント(10_AIプロンプト設計8.2、スキル`flourish-ai`)。

`boto3`の`bedrock-runtime`を直接使わない。`bedrock-mantle`はAnthropicの
Messages APIと同形で、プロンプト設計をそのまま実装できる。IAMロールで認証でき、
APIキーの管理も不要。
"""

from functools import lru_cache

from anthropic import AnthropicBedrockMantle

from app.core.config import get_settings


@lru_cache
def get_client() -> AnthropicBedrockMantle:
    settings = get_settings()
    return AnthropicBedrockMantle(
        aws_region=settings.bedrock_region,
        # SDK自身の自動再試行を切る。429/503/タイムアウトはジョブをFAILEDにして
        # ユーザーの明示的な再試行に委ねる(3.8、破ってはいけない規則5)。
        max_retries=0,
    )
