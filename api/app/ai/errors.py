"""生成失敗の分類(10_AIプロンプト設計3.8、09_API設計5.15)。

`retryable`はクライアントが再試行ボタンを出すかの判断に使う。サーバーは自動で
再試行しない(09_API設計5.15)。
"""

from dataclasses import dataclass

# Bedrock呼び出し自体の失敗(429/503/タイムアウト)。09_API設計5.15の例に倣う。
AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
# スキーマ違反・件数不足がサーバ内再生成(1回)でも解消しなかった。3.8はこの場合の
# retryableを明記していないが、出力は`effort`のみで温度制御がなく揺らぎが残るため
# (2.2)、refusalと違って別ジョブでの再試行が無意味とは言えない。retryable=trueとする。
AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
# stop_reason: "refusal"。同じ入力を再試行しても結果は変わらない。
AI_REFUSED = "AI_REFUSED"
# stop_reason: "max_tokens"。max_tokensの設定ミスとしてアラート対象。
AI_MAX_TOKENS = "AI_MAX_TOKENS"


@dataclass(frozen=True)
class AIGenerationError:
    code: str
    retryable: bool
