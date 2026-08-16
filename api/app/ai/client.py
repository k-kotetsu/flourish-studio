"""Bedrockクライアント(10_AIプロンプト設計8.2、スキル`flourish-ai`)。

`boto3`の`bedrock-runtime`を直接叩かず、Anthropic SDKの`AnthropicBedrock`を使う。
Messages APIと同形で、プロンプト設計をそのまま実装できる。IAMロールで認証でき、
APIキーの管理も不要な点は`AnthropicBedrockMantle`と同じ。

**`AnthropicBedrockMantle`ではなく`AnthropicBedrock`を使う。** 両者は別のAWS
エンドポイントを叩く(`bedrock-mantle.*` / `bedrock-runtime.*`)。P0-2でモデルを
`jp.anthropic.claude-sonnet-4-6`に切り替えた際、`bedrock-mantle`エンドポイントが
このモデル・クロスリージョン推論プロファイルをまだ認識せず404になることを実機で
確認した(P2-13)。`bedrock-runtime`(`AnthropicBedrock`)側では同じモデルが問題なく
呼べ、`output_config`によるJSON拘束・ストリーミングも動作を確認済み。
"""

from functools import lru_cache

from anthropic import AnthropicBedrock

from app.core.config import get_settings


@lru_cache
def get_client() -> AnthropicBedrock:
    settings = get_settings()
    return AnthropicBedrock(
        aws_region=settings.bedrock_region,
        # SDK自身の自動再試行を切る。429/503/タイムアウトはジョブをFAILEDにして
        # ユーザーの明示的な再試行に委ねる(3.8、破ってはいけない規則5)。
        max_retries=0,
    )
