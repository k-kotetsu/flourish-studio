"""JSON Schemaの下ごしらえ(10_AIプロンプト設計3.3)。

Bedrockの`output_config.format`は`minItems`/`maxItems`/`minLength`/`maxLength`を
サポートしない。Bedrockへ渡す版からはこれらを取り除き、件数・文字数を含む完全な
検証はサーバ側(`runner.generate`)で行う。
"""

from typing import Any

_UNSUPPORTED_KEYWORDS = {"minItems", "maxItems", "minLength", "maxLength"}


def to_wire_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Bedrockの`output_config.format.schema`に渡せる形へ変換する。"""
    return {
        key: _strip(value) for key, value in schema.items() if key not in _UNSUPPORTED_KEYWORDS
    }


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip(item) for key, item in value.items() if key not in _UNSUPPORTED_KEYWORDS
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    return value
