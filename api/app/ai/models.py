"""BedrockのモデルID(10_AIプロンプト設計2.1、11_技術構成8.1・8.4)。

モデルは頻繁に更新されるため、切り替えはこのファイルの定数を書き換えるだけで
完結するようにしている(P0-2、11_技術構成8.4「案B」)。
"""

# クロスリージョン推論プロファイル。呼び出しリージョンは`Settings.bedrock_region`
# (既定ap-northeast-1)。`global.anthropic.claude-sonnet-4-6`など別プロファイルへの
# 切り替えもこの1行の書き換えで足りる。
SONNET = "jp.anthropic.claude-sonnet-4-6"
# セーフティ判定(SAFETY_CHECK)のみこちらを使う。
HAIKU = "anthropic.claude-haiku-4-5"
