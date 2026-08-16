"""S-31(ありたい姿：選択式3問)の質問マスタのサーバー側対応表。

S-31自体はクライアント保持のみで何も送信しないが(P3-5)、S-32のAI対話(P3-6、
`POST /ai/purpose-dialogue`)はその選択結果を`choices`としてリクエストに含める
(09_API設計5.6)。プロンプトの`<choices>`ブロック(10_AIプロンプト設計4.3)を組み立てるのに
コード→ラベルの対応表がサーバー側にも要るため、`web/src/domain/purposeChoices.ts`と
1:1で対応するコード・ラベルをここに持つ。文言を変えるときは新しいバージョンを追加し、
既存のcodeは書き換えない(web側と同じ方針)。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import UnprocessableEntityError

Q1 = "Q1"
Q2 = "Q2"
Q3 = "Q3"
QUESTION_CODES = (Q1, Q2, Q3)

# 10_AIプロンプト設計4.3「入力の組み立て」の<choices>ブロックにある表記をそのまま使う
# (web側のUI文言「これからの3〜5年で、大切にしたいことは？」とは別の、プロンプト用の短い表記)。
QUESTION_LABELS: dict[str, str] = {
    Q1: "これからの3〜5年で大切にしたいこと（3つまで）",
    Q2: "満たされていると感じるとき（複数可）",
    Q3: "3〜5年後に送っていたい毎日（1つ）",
}

# web/src/domain/purposeChoices.ts VALUES_OPTIONSと1:1
VALUES_OPTIONS: dict[str, str] = {
    "GROWTH": "成長",
    "STABILITY": "安定",
    "FREEDOM": "自由",
    "CONNECTION": "つながり",
    "CHALLENGE": "挑戦",
    "CONTRIBUTION": "貢献",
    "AUTHENTICITY": "自分らしさ",
    "INTEGRITY": "誠実さ",
    "LEARNING": "学び",
    "HEALTH": "健康",
    "MARGIN": "余白",
    "FAMILY": "家族",
}
VALUES_MAX_SELECTION = 3

# web/src/domain/purposeChoices.ts FULFILLING_MOMENT_OPTIONSと1:1
FULFILLING_MOMENT_OPTIONS: dict[str, str] = {
    "HELPED_SOMEONE": "誰かの役に立てたと感じたとき",
    "NEW_ABILITY": "新しいことができるようになったとき",
    "SELF_DETERMINED": "自分で決められたと感じたとき",
    "TIME_WITH_LOVED_ONES": "大切な人と過ごしているとき",
    "SETTLED_LIFE": "落ち着いた生活が送れているとき",
    "FOCUSED": "集中して何かに取り組めたとき",
    "RECOGNIZED": "認められたと感じたとき",
    "UNSURE": "まだよくわからない",
}

# web/src/domain/purposeChoices.ts IDEAL_DAILY_LIFE_OPTIONSと1:1
IDEAL_DAILY_LIFE_OPTIONS: dict[str, str] = {
    "EXTENSION_OF_NOW": "今の延長線上で、より満足できている",
    "DIFFERENT_PLACE_OR_STYLE": "今とは違う場所や働き方をしている",
    "HAVING_OPTIONS": "選択肢を持てる状態になっている",
    "TIME_FOR_LOVED_ONES": "大切な人との時間が確保できている",
    "ROOM_TO_BREATHE": "心身に余裕がある",
    "CANT_IMAGINE_YET": "まだ想像がつかない",
}

_OPTIONS_BY_QUESTION: dict[str, dict[str, str]] = {
    Q1: VALUES_OPTIONS,
    Q2: FULFILLING_MOMENT_OPTIONS,
    Q3: IDEAL_DAILY_LIFE_OPTIONS,
}

# P3-5完了メモの判断(未回答不可)をサーバー側の検証にも適用する。Q1は1〜3、Q2は1以上、Q3はちょうど1。
_MIN_SELECTIONS: dict[str, int] = {Q1: 1, Q2: 1, Q3: 1}
_MAX_SELECTIONS: dict[str, int | None] = {Q1: VALUES_MAX_SELECTION, Q2: None, Q3: 1}


@dataclass(frozen=True)
class ChoiceAnswer:
    question_code: str
    option_codes: list[str]


def option_labels(question_code: str, option_codes: list[str]) -> list[str]:
    return [_OPTIONS_BY_QUESTION[question_code][code] for code in option_codes]


def validate_choices(choices: list[ChoiceAnswer]) -> None:
    """Q1〜Q3がちょうど1件ずつ、既知の`option_codes`で、件数の上下限を満たすことを確認する。

    `09_API設計`5.6はchoicesの中身の検証を明記していないため、P3-5(S-31)がクライアント側で
    課している制約(全問回答必須。Q1は1〜3、Q2は1以上、Q3はちょうど1)をサーバー側でも
    そのまま適用する判断とした。
    """
    received_codes = [choice.question_code for choice in choices]
    if sorted(received_codes) != sorted(QUESTION_CODES):
        raise UnprocessableEntityError(
            "CHOICES_INVALID", f"choices must have exactly one entry per {QUESTION_CODES}"
        )

    for choice in choices:
        options = _OPTIONS_BY_QUESTION[choice.question_code]
        unknown = [code for code in choice.option_codes if code not in options]
        if unknown:
            raise UnprocessableEntityError(
                "CHOICES_INVALID",
                f"unknown option_codes for {choice.question_code}: {unknown}",
            )

        count = len(choice.option_codes)
        min_count = _MIN_SELECTIONS[choice.question_code]
        max_count = _MAX_SELECTIONS[choice.question_code]
        if count < min_count or (max_count is not None and count > max_count):
            raise UnprocessableEntityError(
                "CHOICES_INVALID",
                f"{choice.question_code} option_codes count out of range (received {count})",
            )
