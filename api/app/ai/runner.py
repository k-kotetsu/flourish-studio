"""プロンプト実行基盤(10_AIプロンプト設計2〜3章、スキル`flourish-ai`)。

system[0]共通ブロック・system[1]個別ブロック・messages入力データの3層を組み立てて
Bedrockを呼び、出力をJSON Schemaで検証する。スキーマ違反・件数不足のときだけ
サーバ内で1回だけ再生成する(3.8)。生成のたびにEMFで記録する(3.9)。

対話(PURPOSE_DIALOGUE/AREA_DIALOGUE)はJSON出力ではなくストリーミングのため、
この`generate`の対象外。各機能タスクが`get_client()`を直接使って実装する。

個別ブロックの本文・出力スキーマは、kindごとの機能タスク(P2以降)が持つ。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import anthropic
import jsonschema
from anthropic.types import (
    JSONOutputFormatParam,
    MessageParam,
    OutputConfigParam,
    TextBlockParam,
)

from app.ai import emf
from app.ai.client import get_client
from app.ai.common_block import COMMON_BLOCK
from app.ai.errors import (
    AI_MAX_TOKENS,
    AI_OUTPUT_INVALID,
    AI_PROVIDER_ERROR,
    AI_REFUSED,
    AIGenerationError,
)
from app.ai.schema import to_wire_schema

Effort = Literal["low", "medium", "high", "xhigh", "max"]

# 429/503相当。タイムアウト・接続断も含め、サーバー側の一時的な不調として扱う(3.8)。
_RETRYABLE_API_ERRORS = (
    anthropic.RateLimitError,
    anthropic.OverloadedError,
    anthropic.InternalServerError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
)


class OutputValidationError(Exception):
    """スキーマ違反・件数不足など、サーバ内再生成の対象になる出力エラー(3.8)。"""


@dataclass(frozen=True)
class PromptSpec:
    kind: str
    model: str
    prompt_version: str
    effort: Effort
    max_tokens: int
    individual_block: str
    schema: dict[str, Any]
    # GOAL_HINTSのみFalse。同期呼び出しで10秒上限があり、2回目の余裕がない
    # (スキル`flourish-ai`「GOAL_HINTSだけ再生成しない」)。
    retry_on_invalid: bool = True


@dataclass(frozen=True)
class GenerationResult:
    status: Literal["SUCCEEDED", "FAILED"]
    output: dict[str, Any] | None = None
    error: AIGenerationError | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cache_read_tokens: int | None = None
    safety_flag: bool | None = None


def generate(
    spec: PromptSpec,
    messages: Sequence[MessageParam],
    *,
    validate_output: Callable[[dict[str, Any]], None] | None = None,
    extra_log_fields: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    attempt: int = 1,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    """1件の生成を行う。

    `validate_output`は、JSON Schemaで表現できない件数・文字数などの追加検証を行う
    (3.3「スキーマで表現できないもの」)。違反時は`OutputValidationError`を送出する。

    `extra_log_fields`は、成功した出力からkind固有のEMFフィールドを作る(例:
    ASSESSMENT_REPORTの`articulation_reason`)。出力が無い(FAILED)ときは呼ばない。

    `attempt`はユーザーが再試行ボタンを押して新しいジョブになったときの通し番号で、
    呼び出し側(ジョブ側)が管理する。同一ジョブ内のサーバ内再生成は`retry_reason`で
    区別され、`attempt`は増えない(08_データモデル7.1)。
    """
    system = _build_system(spec)
    wire_schema = to_wire_schema(spec.schema)

    result = _call(spec, system, wire_schema, messages, validate_output)
    _log(
        spec,
        attempt=attempt,
        retry_reason=None,
        identifiers=identifiers,
        result=result,
        extra_log_fields=extra_log_fields,
    )

    is_retryable_invalid = (
        result.status == "FAILED"
        and result.error is not None
        and result.error.code == AI_OUTPUT_INVALID
        and spec.retry_on_invalid
    )
    if not is_retryable_invalid:
        return result

    result = _call(spec, system, wire_schema, messages, validate_output)
    _log(
        spec,
        attempt=attempt,
        retry_reason="SCHEMA_INVALID",
        identifiers=identifiers,
        result=result,
        extra_log_fields=extra_log_fields,
    )
    return result


def _build_system(spec: PromptSpec) -> list[TextBlockParam]:
    return [
        {"type": "text", "text": COMMON_BLOCK},
        {
            "type": "text",
            "text": spec.individual_block,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _call(
    spec: PromptSpec,
    system: list[TextBlockParam],
    wire_schema: dict[str, Any],
    messages: Sequence[MessageParam],
    validate_output: Callable[[dict[str, Any]], None] | None,
) -> GenerationResult:
    output_format: JSONOutputFormatParam = {"type": "json_schema", "schema": wire_schema}
    output_config: OutputConfigParam = {"effort": spec.effort, "format": output_format}
    try:
        response = get_client().messages.create(
            model=spec.model,
            max_tokens=spec.max_tokens,
            output_config=output_config,
            system=system,
            messages=list(messages),
        )
    except anthropic.APIError as exc:
        retryable = isinstance(exc, _RETRYABLE_API_ERRORS)
        return GenerationResult(
            status="FAILED",
            error=AIGenerationError(AI_PROVIDER_ERROR, retryable=retryable),
        )

    usage = response.usage
    prompt_tokens = usage.input_tokens
    completion_tokens = usage.output_tokens
    cache_read_tokens = usage.cache_read_input_tokens

    # stop_reasonはcontentを読む前に確認する。拒否時はcontentが空になる(3.8)。
    if response.stop_reason == "refusal":
        return GenerationResult(
            status="FAILED",
            error=AIGenerationError(AI_REFUSED, retryable=False),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
        )
    if response.stop_reason == "max_tokens":
        return GenerationResult(
            status="FAILED",
            error=AIGenerationError(AI_MAX_TOKENS, retryable=True),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
        )

    try:
        output = _parse_output(response.content, spec.schema)
        if validate_output is not None:
            validate_output(output)
    except OutputValidationError:
        return GenerationResult(
            status="FAILED",
            error=AIGenerationError(AI_OUTPUT_INVALID, retryable=True),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
        )

    safety_flag = output.get("safety_flag")
    return GenerationResult(
        status="SUCCEEDED",
        output=output,
        safety_flag=safety_flag if isinstance(safety_flag, bool) else None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cache_read_tokens=cache_read_tokens,
    )


def _parse_output(content: list[Any], schema: dict[str, Any]) -> dict[str, Any]:
    if not content:
        raise OutputValidationError("空の応答")
    block = content[0]
    text = getattr(block, "text", None)
    if not isinstance(text, str):
        raise OutputValidationError("テキストブロックではない応答")
    try:
        output = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutputValidationError("JSONとして解釈できない応答") from exc
    if not isinstance(output, dict):
        raise OutputValidationError("オブジェクトではない応答")
    try:
        jsonschema.validate(output, schema)
    except jsonschema.ValidationError as exc:
        raise OutputValidationError(str(exc)) from exc
    return output


def _log(
    spec: PromptSpec,
    *,
    attempt: int,
    retry_reason: str | None,
    identifiers: dict[str, str] | None,
    result: GenerationResult,
    extra_log_fields: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> None:
    extra = None
    if extra_log_fields is not None and result.output is not None:
        extra = extra_log_fields(result.output)
    emf.emit(
        kind=spec.kind,
        model=spec.model,
        prompt_version=spec.prompt_version,
        effort=spec.effort,
        status=result.status,
        attempt=attempt,
        retry_reason=retry_reason,
        error_code=result.error.code if result.error else None,
        safety_flag=result.safety_flag,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cache_read_tokens=result.cache_read_tokens,
        identifiers=identifiers,
        extra=extra,
    )
