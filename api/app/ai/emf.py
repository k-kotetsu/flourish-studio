"""生成のたびにEMF(埋め込みメトリクス形式)でCloudWatchへ記録する
(10_AIプロンプト設計3.9、11_技術構成8.6、08_データモデル7章)。DBには置かない。

標準出力へEMF形式のJSONを1行書けば、Lambdaのログがそのまま
CloudWatch LogsからEMFメトリクスとして抽出される。プロンプトの入出力本文は出さない
(対話の本文・成果物は既にDBにある)。
"""

import json
import time
from typing import Any, Literal

_NAMESPACE = "FlourishStudio/AIGeneration"
_DIMENSIONS = ["kind", "model", "status"]


def emit(
    *,
    kind: str,
    model: str,
    prompt_version: str,
    effort: str,
    status: Literal["SUCCEEDED", "FAILED"],
    attempt: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cache_read_tokens: int | None = None,
    retry_reason: str | None = None,
    error_code: str | None = None,
    safety_flag: bool | None = None,
    identifiers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """1回のBedrock呼び出しにつき1行を出す。

    `retry_reason`は同一ジョブ内のサーバ内再生成を区別する。`attempt`はユーザーが
    再試行ボタンを押して新しいジョブになったときだけ増える値で、呼び出し側が渡す
    (08_データモデル7.1「再試行は同じkindで新しいログを出し、attemptを増やす」)。

    `extra`はkind固有のフィールド(例: ASSESSMENT_REPORTの`articulation_reason`。
    10_AIプロンプト設計4.2「ASSESSMENT_RESULTに保存せず、AI_GENERATION側に記録する」)。
    08_データモデル7.1の共通フィールド一覧には無いため、この引数でしか渡らない。
    """
    payload: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": _NAMESPACE,
                    "Dimensions": [_DIMENSIONS],
                    "Metrics": [
                        {"Name": "PromptTokens", "Unit": "Count"},
                        {"Name": "CompletionTokens", "Unit": "Count"},
                        {"Name": "CacheReadTokens", "Unit": "Count"},
                    ],
                }
            ],
        },
        "kind": kind,
        "model": model,
        "status": status,
        "prompt_version": prompt_version,
        "effort": effort,
        "attempt": attempt,
        "retry_reason": retry_reason,
        "error_code": error_code,
        "safety_flag": safety_flag,
        "PromptTokens": prompt_tokens or 0,
        "CompletionTokens": completion_tokens or 0,
        "CacheReadTokens": cache_read_tokens or 0,
    }
    if identifiers:
        payload.update(identifiers)
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))
