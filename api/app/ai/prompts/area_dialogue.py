"""P-05 `AREA_DIALOGUE`(10_AIプロンプト設計4.5)。S-52の領域AI対話。

`PURPOSE_DIALOGUE`(P-03、`purpose_dialogue.py`)と「同じルール・同じ承認の入れ方」
(05_質問・コンテンツ設計9.3)のため、`DialogueMessage`・`compute_turn`・
`build_conversation_block`はそちらから再利用する(`PURPOSE_PROPOSALS`が
`purpose_dialogue`のビルダー関数を共有するのと同じ考え方)。

**往復数はコードが数える。** P-03と同じく、AIには`<turn>`で現在の往復目を渡すだけで、
残り回数の計算はさせない(スキル`flourish-ai`「AIにやらせないこと」)。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

import anthropic
from anthropic.types import MessageParam, TextBlockParam

from app.ai import emf
from app.ai.client import get_client
from app.ai.common_block import COMMON_BLOCK
from app.ai.errors import AI_MAX_TOKENS, AI_OUTPUT_INVALID, AI_PROVIDER_ERROR, AI_REFUSED
from app.ai.models import SONNET
from app.ai.prompts.purpose_dialogue import DialogueMessage, build_conversation_block
from app.ai.prompts.safety_check import check_safety
from app.domain.area_choices import QUESTION_CODES, QUESTION_LABELS, ChoiceAnswer, option_labels
from app.domain.questions import AREA_LABELS

_logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-08-v1"
# 10_AIプロンプト設計4.5は`medium`/4,000を指定するが、スキルflourish-aiの対応表は
# `low`/3,000で食い違っている(`PURPOSE_DIALOGUE`と同じ行にまとめられている)。
# P2-5・P2-8・P3-6・P3-7完了メモで確立した「ドキュメント優先」を踏襲し、4.5の値を
# 採用した(5件目の同種の食い違い。スキル側の表は未修正のまま残る)。
EFFORT = "medium"
MAX_TOKENS = 4000
TOTAL_TURNS = 2
# 4.3「検証」を踏襲(9.3「P-03と同じルール」): 400文字を超えても不合格にはしない。警告ログのみ。
_WARN_TEXT_LENGTH = 400

AI_ROLE = "AI"
USER_ROLE = "USER"

INDIVIDUAL_BLOCK = """# あなたの仕事
ユーザーが、この領域の「1年後の理想の状態」を言葉にできるよう、対話で引き出します。
全部で約2往復です。

# 1回の返答の形
「受け止める一文」＋「問い1つ」。P-03 と同じです。3文以内を目安にします。

# 往復ごとの狙い
1往復目: 大切にしたいことの背景を引き出す。
  Q1で選んだ項目と、Q2で選んだ「大切にしたいこと」を結びつけ、
  なぜそれが自分にとって大事なのかを聞きます。
2往復目: ありたい姿につなげる。
  Q3で選んだ位置づけをふまえ、それが実現したとき、
  確定済みの「ありたい姿」にどう近づくのかを聞きます。

# ありたい姿の扱い
<purpose> に渡される一文は、ユーザーが自分で確定させたものです。
- 言い換えません。要約しません。引用するときは一字一句そのまま使います。
- 内容を評価しません。
- 2往復目では必ずこの一文に触れ、領域とのつながりを聞きます。

# 承認の入れ方
2往復のうち多くて1回です。P-03 と同じ条件を守ります。

# 出力
本文だけを出力します。見出し、箇条書き、記号による装飾を使いません。"""


def _escape_user_input(text: str) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(スキルflourish-ai、purpose_dialogue.pyと同じ)。"""
    return text.replace("<", "&lt;")


def build_choices_block(area: str, choices: list[ChoiceAnswer]) -> str:
    by_code = {choice.question_code: choice for choice in choices}
    lines = []
    for code in QUESTION_CODES:
        choice = by_code[code]
        labels = " / ".join(option_labels(area, code, choice.option_codes))
        lines.append(f"{code} {QUESTION_LABELS[area][code]}: {labels}")
    return "\n".join(lines)


def build_messages(
    purpose_statement: str,
    area: str,
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
    turn: int,
) -> list[MessageParam]:
    """4.5「入力の組み立て」のとおり`<purpose>`・`<area>`・`<choices>`・`<turn>`・
    `<conversation>`を組み立てる。`turn`が`TOTAL_TURNS`を超える場合の頭打ちは
    P-03(`purpose_dialogue.build_messages`)と同じ判断を踏襲する。
    """
    prompt_turn = min(turn, TOTAL_TURNS)
    escaped_purpose = _escape_user_input(purpose_statement)
    content = (
        f"<purpose>\n確定した「ありたい姿」: {escaped_purpose}\n</purpose>\n\n"
        f"<area>\n対象領域: {AREA_LABELS[area]}\n</area>\n\n"
        f"<choices>\n{build_choices_block(area, choices)}\n</choices>\n\n"
        f"<turn>\n現在: {prompt_turn}往復目 / 全{TOTAL_TURNS}往復\n</turn>\n\n"
        f"<conversation>\n{build_conversation_block(messages)}\n</conversation>"
    )
    return [{"role": "user", "content": content}]


def _build_system() -> list[TextBlockParam]:
    return [
        {"type": "text", "text": COMMON_BLOCK},
        {"type": "text", "text": INDIVIDUAL_BLOCK, "cache_control": {"type": "ephemeral"}},
    ]


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _log(
    *,
    status: Literal["SUCCEEDED", "FAILED"],
    error_code: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cache_read_tokens: int | None = None,
    identifiers: dict[str, str] | None,
) -> None:
    # PURPOSE_DIALOGUEと同じ理由で常にNone(この生成自体はプレーンテキストで、
    # safety_flagはSAFETY_CHECK側が自分のEMF行に別途記録する)。
    emf.emit(
        kind="AREA_DIALOGUE",
        model=SONNET,
        prompt_version=PROMPT_VERSION,
        effort=EFFORT,
        status=status,
        attempt=1,
        error_code=error_code,
        safety_flag=None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cache_read_tokens=cache_read_tokens,
        identifiers=identifiers,
    )


def stream_reply(
    purpose_statement: str,
    area: str,
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
    turn: int,
    *,
    identifiers: dict[str, str] | None = None,
) -> Iterator[str]:
    """SSEイベント文字列を`delta`→`done`の順で生成する。PURPOSE_DIALOGUEの
    `stream_reply`と同じ構造(セーフティ判定の案B含む)。TOTAL_TURNSのみ2に変わる。
    """
    system = _build_system()
    api_messages = build_messages(purpose_statement, area, choices, messages, turn)

    safety_executor: ThreadPoolExecutor | None = None
    if messages and messages[-1].role == USER_ROLE:
        safety_executor = ThreadPoolExecutor(max_workers=1)
        safety_future = safety_executor.submit(
            check_safety, messages[-1].body, identifiers=identifiers
        )

    try:
        text_parts: list[str] = []
        try:
            with get_client().messages.stream(
                model=SONNET,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=api_messages,
            ) as stream:
                for text in stream.text_stream:
                    text_parts.append(text)
                    yield _sse("delta", {"text": text})
                final_message = stream.get_final_message()
        except anthropic.APIError:
            _log(
                status="FAILED",
                error_code=AI_PROVIDER_ERROR,
                prompt_tokens=None,
                completion_tokens=None,
                identifiers=identifiers,
            )
            yield _sse("error", {"code": AI_PROVIDER_ERROR})
            return

        prompt_tokens = final_message.usage.input_tokens
        completion_tokens = final_message.usage.output_tokens
        cache_read_tokens = final_message.usage.cache_read_input_tokens

        # stop_reasonはcontentを読む前に確認する。拒否時はcontentが空になる(3.8)。
        if final_message.stop_reason == "refusal":
            _log(
                status="FAILED",
                error_code=AI_REFUSED,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_read_tokens=cache_read_tokens,
                identifiers=identifiers,
            )
            yield _sse("error", {"code": AI_REFUSED})
            return
        if final_message.stop_reason == "max_tokens":
            _log(
                status="FAILED",
                error_code=AI_MAX_TOKENS,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_read_tokens=cache_read_tokens,
                identifiers=identifiers,
            )
            yield _sse("error", {"code": AI_MAX_TOKENS})
            return

        full_text = "".join(text_parts)
        if not full_text:
            _log(
                status="FAILED",
                error_code=AI_OUTPUT_INVALID,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_read_tokens=cache_read_tokens,
                identifiers=identifiers,
            )
            yield _sse("error", {"code": AI_OUTPUT_INVALID})
            return

        if len(full_text) > _WARN_TEXT_LENGTH:
            _logger.warning(
                "AREA_DIALOGUE output exceeded %d chars (%d)",
                _WARN_TEXT_LENGTH,
                len(full_text),
            )

        safety_flag = False
        if safety_executor is not None:
            safety_flag = safety_future.result().flagged

        remaining = max(0, TOTAL_TURNS - turn)
        _log(
            status="SUCCEEDED",
            error_code=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
            identifiers=identifiers,
        )
        yield _sse("done", {"turn": turn, "remaining": remaining, "safety_flag": safety_flag})
    finally:
        if safety_executor is not None:
            safety_executor.shutdown(wait=True)
