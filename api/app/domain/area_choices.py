"""S-51(領域：選択式質問)の質問マスタのサーバー側対応表。

S-51自体はクライアント保持のみで何も送信しないが(04_画面設計 screen-list.md S-51「保存: しない」、
P4-2)、S-52のAI対話(P4-3、`POST /ai/area-dialogue`)はその選択結果を`choices`として
リクエストに含める(`09_API設計`6章の画面対応表、`10_AIプロンプト設計`4.5)。プロンプトの
`<choices>`ブロックを組み立てるのにコード→ラベルの対応表がサーバー側にも要るため、
`web/src/domain/areaChoices.ts`と1:1で対応するコード・ラベルをここに持つ。文言を変えるときは
新しいバージョンを追加し、既存のcodeは書き換えない(web側と同じ方針)。

Q1(いちばん変えたい項目)はS-12と同じ5項目(`app.domain.questions`のAreaItem)をそのまま使う
(05_質問・コンテンツ設計9.2「現在地レポートで使った5項目をそのまま提示する」)ため、
このモジュールには持たない(`web/src/domain/areaChoices.ts`と同じ設計)。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import UnprocessableEntityError
from app.domain.questions import CURRENT_QUESTION_SET_VERSION, get_question_set

Q1 = "Q1"
Q2 = "Q2"
Q3 = "Q3"
QUESTION_CODES = (Q1, Q2, Q3)

# 10_AIプロンプト設計4.5「入力の組み立て」の例にある表記をそのまま使う(Careerのみ明記)。
# 他領域は同じパターンで領域名の名詞だけを差し替えた(プロンプト用の短い表記。
# UIの設問文`AREA_VALUES_PROMPT`/`AREA_POSITION_PROMPT`とは別。purpose_choices.pyの
# QUESTION_LABELSと同じ考え方)。
QUESTION_LABELS: dict[str, dict[str, str]] = {
    "CAREER": {
        Q1: "3〜5年後にいちばん変わっていてほしいこと（1つ）",
        Q2: "これからの仕事で特に大切にしたいこと（複数）",
        Q3: "仕事は人生の中でどんな存在であってほしいか（複数）",
    },
    "FINANCIAL": {
        Q1: "3〜5年後にいちばん変わっていてほしいこと（1つ）",
        Q2: "これからのお金で特に大切にしたいこと（複数）",
        Q3: "お金は人生の中でどんな存在であってほしいか（複数）",
    },
    "PHYSICAL": {
        Q1: "3〜5年後にいちばん変わっていてほしいこと（1つ）",
        Q2: "これからのからだで特に大切にしたいこと（複数）",
        Q3: "からだは人生の中でどんな存在であってほしいか（複数）",
    },
    "SOCIAL": {
        Q1: "3〜5年後にいちばん変わっていてほしいこと（1つ）",
        Q2: "これからの人との関係で特に大切にしたいこと（複数）",
        Q3: "人との関係は人生の中でどんな存在であってほしいか（複数）",
    },
}

# web/src/domain/areaChoices.ts CAREER_VALUES_OPTIONSと1:1
_CAREER_VALUES_OPTIONS: dict[str, str] = {
    "CAREER_VALUE_GROWTH": "自分の成長を実感できること",
    "CAREER_VALUE_CONTRIBUTION": "誰かの役に立っている手ごたえ",
    "CAREER_VALUE_RECOGNITION": "正当に評価されること",
    "CAREER_VALUE_RELATIONSHIPS": "一緒に働く人との相性",
    "CAREER_VALUE_AUTONOMY": "自分で決められる裁量があること",
    "CAREER_VALUE_STABILITY": "安定して続けられること",
    "CAREER_VALUE_INCOME_GROWTH": "収入が上がっていくこと",
    "CAREER_VALUE_CHALLENGE": "新しいことに挑戦できること",
    "CAREER_VALUE_EXPERTISE": "専門性を深められること",
    "CAREER_VALUE_WORK_LIFE_BALANCE": "生活を圧迫しない働き方であること",
}

# web/src/domain/areaChoices.ts CAREER_POSITION_OPTIONSと1:1
_CAREER_POSITION_OPTIONS: dict[str, str] = {
    "CAREER_POSITION_EXPRESSION": "自分を表現する場であってほしい",
    "CAREER_POSITION_MEANS": "生活を支える手段であればいい",
    "CAREER_POSITION_GROWTH": "成長し続けられる場であってほしい",
    "CAREER_POSITION_CONNECTION": "人とのつながりが生まれる場であってほしい",
    "CAREER_POSITION_TESTING_GROUND": "自分の力を試せる場であってほしい",
    "CAREER_POSITION_LOW_STRESS": "心をすり減らさない場であってほしい",
    "CAREER_POSITION_CENTER": "人生の中心にあってほしい",
    "CAREER_POSITION_PERIPHERAL": "人生の一部くらいの距離でいてほしい",
    "CAREER_POSITION_PRIDE": "誇りを持てる場であってほしい",
    "CAREER_POSITION_FLEXIBLE": "いつでも変えられる選択肢のひとつでいてほしい",
}

# web/src/domain/areaChoices.ts FINANCIAL_VALUES_OPTIONSと1:1
_FINANCIAL_VALUES_OPTIONS: dict[str, str] = {
    "FINANCIAL_VALUE_REDUCE_ANXIETY": "将来の不安を減らすこと",
    "FINANCIAL_VALUE_MAINTAIN_QUALITY": "今の生活の質を落とさないこと",
    "FINANCIAL_VALUE_AUTONOMY": "使い道を自分で決められること",
    "FINANCIAL_VALUE_PREPAREDNESS": "想定外の出来事に備えられること",
    "FINANCIAL_VALUE_INCOME_GROWTH": "収入を増やしていくこと",
    "FINANCIAL_VALUE_ORGANIZATION": "無駄をなくして整えること",
    "FINANCIAL_VALUE_FOR_LOVED_ONES": "大切な人のために使えること",
    "FINANCIAL_VALUE_LESS_WORRY": "お金のことで悩む時間を減らすこと",
    "FINANCIAL_VALUE_NO_COMPROMISE": "やりたいことを諦めずに済むこと",
    "FINANCIAL_VALUE_ASSET_BUILDING": "資産を計画的に増やしていくこと",
}

# web/src/domain/areaChoices.ts FINANCIAL_POSITION_OPTIONSと1:1
_FINANCIAL_POSITION_OPTIONS: dict[str, str] = {
    "FINANCIAL_POSITION_UNCONSCIOUS": "意識せずに済む存在であってほしい",
    "FINANCIAL_POSITION_OPTIONS": "選択肢を広げてくれる存在であってほしい",
    "FINANCIAL_POSITION_FOUNDATION": "安心の土台であってほしい",
    "FINANCIAL_POSITION_MARGIN": "自由に使える余裕があってほしい",
    "FINANCIAL_POSITION_MEASURE": "目標を測るものさしであってほしい",
    "FINANCIAL_POSITION_SUPPORT_OTHERS": "誰かを支えるために使えるものであってほしい",
    "FINANCIAL_POSITION_ENJOY_GROWING": "増やすこと自体を楽しめるものであってほしい",
    "FINANCIAL_POSITION_SUFFICIENT": "生活が回れば十分な存在でいてほしい",
    "FINANCIAL_POSITION_FUTURE_SELF": "将来の自分への仕送りであってほしい",
    "FINANCIAL_POSITION_NO_ANXIETY": "不安の種にならない存在であってほしい",
}

# web/src/domain/areaChoices.ts PHYSICAL_VALUES_OPTIONSと1:1
_PHYSICAL_VALUES_OPTIONS: dict[str, str] = {
    "PHYSICAL_VALUE_DAILY_ENERGY": "毎日を元気に過ごせること",
    "PHYSICAL_VALUE_RECOVERY": "疲れを翌日に持ち越さないこと",
    "PHYSICAL_VALUE_APPEARANCE": "見た目に納得できること",
    "PHYSICAL_VALUE_LONGEVITY": "長く健康でいられること",
    "PHYSICAL_VALUE_SLEEP": "よく眠れること",
    "PHYSICAL_VALUE_SUSTAINABLE_HABIT": "無理のない習慣にできること",
    "PHYSICAL_VALUE_MOOD_STABILITY": "気分が安定していること",
    "PHYSICAL_VALUE_STAMINA": "体力に自信を持てること",
    "PHYSICAL_VALUE_REDUCE_ILLNESS_ANXIETY": "病気の不安を減らすこと",
    "PHYSICAL_VALUE_ENJOY_MOVEMENT": "からだを動かすことを楽しめること",
}

# web/src/domain/areaChoices.ts PHYSICAL_POSITION_OPTIONSと1:1
_PHYSICAL_POSITION_OPTIONS: dict[str, str] = {
    "PHYSICAL_POSITION_CARE_FREE": "何も気にせずにいられる存在であってほしい",
    "PHYSICAL_POSITION_SUPPORT_GOALS": "やりたいことを支えてくれる存在であってほしい",
    "PHYSICAL_POSITION_SELF_CARE": "自分を大事にしている実感になってほしい",
    "PHYSICAL_POSITION_ENJOY_MAINTAINING": "整えること自体が楽しみであってほしい",
    "PHYSICAL_POSITION_CONFIDENCE": "自信の源であってほしい",
    "PHYSICAL_POSITION_RHYTHM": "生活のリズムを作るものであってほしい",
    "PHYSICAL_POSITION_LONG_TERM": "年を重ねても付き合っていける存在であってほしい",
    "PHYSICAL_POSITION_LIMITER": "頑張りすぎを止めてくれる存在であってほしい",
    "PHYSICAL_POSITION_MOOD_RESET": "気分を切り替える手段であってほしい",
    "PHYSICAL_POSITION_SHARED_ENJOYMENT": "誰かと一緒に楽しめるものであってほしい",
}

# web/src/domain/areaChoices.ts SOCIAL_VALUES_OPTIONSと1:1
_SOCIAL_VALUES_OPTIONS: dict[str, str] = {
    "SOCIAL_VALUE_EASE": "気を使わずにいられること",
    "SOCIAL_VALUE_RELIABILITY": "困ったときに頼れること",
    "SOCIAL_VALUE_HONESTY": "本音で話せること",
    "SOCIAL_VALUE_ENJOYMENT": "一緒にいて楽しいこと",
    "SOCIAL_VALUE_BEING_USEFUL": "相手の力になれること",
    "SOCIAL_VALUE_NO_FORCING": "無理して合わせなくていいこと",
    "SOCIAL_VALUE_LONGEVITY": "長く続いていくこと",
    "SOCIAL_VALUE_NEW_ENCOUNTERS": "新しい出会いがあること",
    "SOCIAL_VALUE_MUTUAL_RESPECT": "お互いを認め合えること",
    "SOCIAL_VALUE_RESPECT_SOLITUDE": "ひとりの時間も尊重されること",
}

# web/src/domain/areaChoices.ts SOCIAL_POSITION_OPTIONSと1:1
_SOCIAL_POSITION_OPTIONS: dict[str, str] = {
    "SOCIAL_POSITION_SAFE_HAVEN": "安心して戻れる場所であってほしい",
    "SOCIAL_POSITION_STIMULATION": "刺激をくれる存在であってほしい",
    "SOCIAL_POSITION_SELF_DISCOVERY": "自分を知るきっかけであってほしい",
    "SOCIAL_POSITION_MUTUAL_SUPPORT": "支え合える関係であってほしい",
    "SOCIAL_POSITION_FEW_BUT_DEEP": "数は少なくても、濃くありたい",
    "SOCIAL_POSITION_WIDE_AND_LOOSE": "広く、ゆるやかにつながっていたい",
    "SOCIAL_POSITION_AUTHENTICITY": "自分らしくいられる場であってほしい",
    "SOCIAL_POSITION_LIFE_COMPANION": "人生を一緒に歩む存在であってほしい",
    "SOCIAL_POSITION_AS_NEEDED": "必要なときにだけあればいい",
    "SOCIAL_POSITION_BEING_A_HAVEN": "誰かの居場所になれる関係であってほしい",
}

_VALUES_OPTIONS_BY_AREA: dict[str, dict[str, str]] = {
    "CAREER": _CAREER_VALUES_OPTIONS,
    "FINANCIAL": _FINANCIAL_VALUES_OPTIONS,
    "PHYSICAL": _PHYSICAL_VALUES_OPTIONS,
    "SOCIAL": _SOCIAL_VALUES_OPTIONS,
}

_POSITION_OPTIONS_BY_AREA: dict[str, dict[str, str]] = {
    "CAREER": _CAREER_POSITION_OPTIONS,
    "FINANCIAL": _FINANCIAL_POSITION_OPTIONS,
    "PHYSICAL": _PHYSICAL_POSITION_OPTIONS,
    "SOCIAL": _SOCIAL_POSITION_OPTIONS,
}

# Q2・Q3は上限を設けない(9.2に上限の記載がなく、S-51〔P4-2〕がクライアント側で
# 下した判断をサーバー側にも適用する)。Q1はS-51と同じく単一選択。
_MIN_SELECTIONS: dict[str, int] = {Q1: 1, Q2: 1, Q3: 1}
_MAX_SELECTIONS: dict[str, int | None] = {Q1: 1, Q2: None, Q3: None}


@dataclass(frozen=True)
class ChoiceAnswer:
    question_code: str
    option_codes: list[str]


def _item_labels(area: str) -> dict[str, str]:
    items = get_question_set(CURRENT_QUESTION_SET_VERSION).items
    return {item.code: item.label for item in items if item.area == area}


def _options_for(area: str, question_code: str) -> dict[str, str]:
    if question_code == Q1:
        return _item_labels(area)
    if question_code == Q2:
        return _VALUES_OPTIONS_BY_AREA[area]
    return _POSITION_OPTIONS_BY_AREA[area]


def option_labels(area: str, question_code: str, option_codes: list[str]) -> list[str]:
    options = _options_for(area, question_code)
    return [options[code] for code in option_codes]


def validate_area_choices(area: str, choices: list[ChoiceAnswer]) -> None:
    """Q1〜Q3がちょうど1件ずつ、既知の`option_codes`で、件数の上下限を満たすことを確認する。

    S-51(P4-2)がクライアント側で課している制約(全問回答必須。Q1はちょうど1、Q2・Q3は
    1件以上で上限なし)を、`purpose_choices.validate_choices`と同じ考え方でサーバー側にも
    そのまま適用する判断とした。
    """
    received_codes = [choice.question_code for choice in choices]
    if sorted(received_codes) != sorted(QUESTION_CODES):
        raise UnprocessableEntityError(
            "CHOICES_INVALID", f"choices must have exactly one entry per {QUESTION_CODES}"
        )

    for choice in choices:
        options = _options_for(area, choice.question_code)
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
