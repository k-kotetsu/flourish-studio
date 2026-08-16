"""P-03 `PURPOSE_DIALOGUE`(10_AIプロンプト設計4.3)。S-32のありたい姿AI対話。

構造化出力を使わないプレーンテキストのストリーミングのため、JSON Schema検証・
サーバ内再生成を前提にした`app.ai.runner.generate`は使わない(runner.pyのモジュール
docstringのとおり)。共通ブロックを使わない`safety_check.py`と同じく、この
モジュールが専用の呼び出し経路(`stream_reply`)を持つ。

**往復数はコードが数える。** AIには`<turn>`で現在の往復目を渡すだけで、
残り回数の計算はさせない(4.3、スキル`flourish-ai`「AIにやらせないこと」)。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal

import anthropic
from anthropic.types import MessageParam, TextBlockParam

from app.ai import emf
from app.ai.client import get_client
from app.ai.common_block import COMMON_BLOCK
from app.ai.errors import AI_MAX_TOKENS, AI_OUTPUT_INVALID, AI_PROVIDER_ERROR, AI_REFUSED
from app.ai.models import SONNET
from app.ai.prompts.safety_check import check_safety
from app.core.errors import BadRequestError
from app.domain.purpose_choices import QUESTION_CODES, QUESTION_LABELS, ChoiceAnswer, option_labels

_logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-08-v1"
# 10_AIプロンプト設計4.3は`medium`/4,000を指定するが、スキルflourish-aiの対応表は
# `low`/3,000で食い違っている。P2-5・P2-8完了メモで確立した「ドキュメント優先」を
# 踏襲し、4.3の値を採用した(3件目の同種の食い違い。スキル側の表は未修正のまま残る)。
EFFORT = "medium"
MAX_TOKENS = 4000
TOTAL_TURNS = 3
# 4.3「検証」: 400文字を超えても不合格にはしない。警告ログのみで表示は行う。
_WARN_TEXT_LENGTH = 400

AI_ROLE = "AI"
USER_ROLE = "USER"

INDIVIDUAL_BLOCK = """# あなたの仕事
ユーザーが自分の「ありたい姿」を言葉にできるよう、対話で引き出します。
全部で約3往復です。何往復目かは <turn> で渡されます。

# 1回の返答の形
「受け止める一文」＋「問い1つ」で構成します。これを毎回守ります。
- 問いは1つだけです。2つ聞きません。
- 答えを提示しません。問いで返します。
- 選択肢を並べて選ばせません。
- 長くしません。全体で3文以内を目安にします。

# 往復ごとの狙い
1往復目: 選んだ価値観の背景を引き出す。
  選択式で最も特徴的だった回答を取り上げ、なぜそれを選んだのかを聞きます。
  起点の例: 「{選んだ価値観}」を選ばれていました。
  これを選んだのは、何か思い当たることがありましたか。
2往復目: 具体的な場面に降ろす。
  それを感じた実際の経験や場面を聞きます。
3往復目: 将来につなげる。
  その感覚が3〜5年後にどうなっていてほしいかを聞きます。

# 承認の入れ方
3往復のうち1〜2回だけ、承認を入れます。毎回は入れません。
承認するときは、ユーザーが書いた言葉を引用したうえで、どこが良かったのかを示します。

避ける例:
  素晴らしいですね。
  よく考えられていますね。
望ましい例:
  「まわりが安心して力を出せるように」と書かれていました。ここは自分の言葉になっていると思います。それはどんな場面で感じたことですか。
  迷っていると書きながら、選ばなかった理由まで書かれていました。何がそう思わせたのでしょう。

# ユーザーが書けないとき
「わからない」「特にない」と返ってきた場合、問い詰めません。
問いの角度を変えます。抽象度を下げ、過去の具体的な出来事を聞く方向に寄せます。

# 出力
本文だけを出力します。見出し、箇条書き、記号による装飾を使いません。"""


@dataclass(frozen=True)
class DialogueMessage:
    role: Literal["AI", "USER"]
    body: str


def compute_turn(messages: list[DialogueMessage]) -> int:
    """往復数を数える。`messages`はAI→USER→AI→USER…と交互に並び、末尾はUSERであるはず
    (次に生成するのはAIの番のため)。09_API設計5.6は空配列(1往復目)も許す。

    崩れた並びは、クライアントの実装不備として`400 MESSAGES_INVALID`にする
    (仕様に明記のない経路。P2-5の`QUESTION_SET_VERSION_UNKNOWN`と同じ判断)。
    """
    if messages and messages[-1].role != USER_ROLE:
        raise BadRequestError("MESSAGES_INVALID", "the last message must be from USER")
    for index, message in enumerate(messages):
        expected_role = AI_ROLE if index % 2 == 0 else USER_ROLE
        if message.role != expected_role:
            raise BadRequestError(
                "MESSAGES_INVALID", "messages must alternate starting with AI"
            )
    ai_turns = sum(1 for message in messages if message.role == AI_ROLE)
    return ai_turns + 1


def _escape_user_input(text: str) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(スキルflourish-ai)。"""
    return text.replace("<", "&lt;")


def build_choices_block(choices: list[ChoiceAnswer]) -> str:
    """`<choices>`の中身の組み立て。P-04(`purpose_proposals.py`)も同じ入力形式
    (「P-03と同じ形式」10_AIプロンプト設計4.4)のため、モジュール間で共有する。
    """
    by_code = {choice.question_code: choice for choice in choices}
    lines = []
    for code in QUESTION_CODES:
        choice = by_code[code]
        labels = " / ".join(option_labels(code, choice.option_codes))
        lines.append(f"{code} {QUESTION_LABELS[code]}: {labels}")
    return "\n".join(lines)


def build_conversation_block(messages: list[DialogueMessage]) -> str:
    """`<conversation>`の中身の組み立て。`build_choices_block`と同じ理由でP-04と共有する。"""
    lines = []
    for message in messages:
        if message.role == AI_ROLE:
            lines.append(f"AI: {message.body}")
        else:
            lines.append(f"USER: <user_input>{_escape_user_input(message.body)}</user_input>")
    return "\n".join(lines)


def build_messages(
    choices: list[ChoiceAnswer], messages: list[DialogueMessage], turn: int
) -> list[MessageParam]:
    """4.3「入力の組み立て」のとおり`<choices>`・`<turn>`・`<conversation>`を組み立てる。

    `turn`は3を超えることがある(wireframe-spec.md「3往復完了後も入力欄は残す」で
    ユーザーが対話を続けられるため)。個別ブロックの「往復ごとの狙い」は3往復目までしか
    定義していないため、AIに渡す`<turn>`表示は3で頭打ちにする(3往復目の狙い「将来に
    つなげる」を続けるのが自然な落とし所と判断した)。
    """
    prompt_turn = min(turn, TOTAL_TURNS)
    content = (
        f"<choices>\n{build_choices_block(choices)}\n</choices>\n\n"
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
    # `safety_flag`はこの生成自体の出力に含まれない(プレーンテキストで、判定は
    # 別のSAFETY_CHECK呼び出しが行う)。SAFETY_CHECK側のEMF行(check_safetyが自ら記録する)
    # に別途残るため、ここは常にNoneとする。
    emf.emit(
        kind="PURPOSE_DIALOGUE",
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
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
    turn: int,
    *,
    identifiers: dict[str, str] | None = None,
) -> Iterator[str]:
    """SSEイベント文字列(`event: ... \\ndata: ...\\n\\n`)を`delta`→`done`の順で生成する。

    失敗時は`error`イベントを1つ返して終える(自動リトライしない。破ってはいけない規則5)。
    直近のUSER発言があれば、`claude-haiku-4-5`のSAFETY_CHECKを別スレッドで並行実行し、
    本文生成をブロックしない(4.3「案B」、スキルflourish-ai)。
    """
    system = _build_system()
    api_messages = build_messages(choices, messages, turn)

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
                "PURPOSE_DIALOGUE output exceeded %d chars (%d)",
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
