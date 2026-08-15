"""選択式(S-12)の質問マスタ。05_質問・コンテンツ設計2章、08_データモデル1.2、9章。

文言を変えるときは`QUESTION_SETS`に新しいバージョンを追加する。
過去バージョンの定義は消さない(08_データモデル1.2「マスタをコードに置くことへの対処」)。
保存済みの`assessment.question_set_version`から、そのとき何と表示されていたかを復元できる必要があるため。
"""

from dataclasses import dataclass

CAREER = "CAREER"
FINANCIAL = "FINANCIAL"
PHYSICAL = "PHYSICAL"
SOCIAL = "SOCIAL"
AREAS = (CAREER, FINANCIAL, PHYSICAL, SOCIAL)

SATISFACTION = "SATISFACTION"
COMMITMENT = "COMMITMENT"
QUESTION_KINDS = (SATISFACTION, COMMITMENT)

# プロンプト入力での領域表記(10_AIプロンプト設計4.1「領域: Career（仕事・働き方）」)。
# web/src/domain/questions.ts の`AREA_META`のen/jpと揃える。
AREA_LABELS: dict[str, str] = {
    CAREER: "Career（仕事・働き方）",
    FINANCIAL: "Financial（お金・生活設計）",
    PHYSICAL: "Physical（健康・生活習慣）",
    SOCIAL: "Social（人との関係）",
}

# 英語表記のみ(10_AIプロンプト設計4.2「充足感が最も高い領域: Career」)。
# web/src/domain/questions.ts の`AREA_META`の`en`と揃える。
AREA_EN_LABELS: dict[str, str] = {
    CAREER: "Career",
    FINANCIAL: "Financial",
    PHYSICAL: "Physical",
    SOCIAL: "Social",
}


@dataclass(frozen=True)
class Choice:
    score: int
    label: str


@dataclass(frozen=True)
class AreaItem:
    code: str
    area: str
    label: str


@dataclass(frozen=True)
class QuestionSet:
    version: str
    satisfaction_prompt: str
    commitment_prompt: str
    satisfaction_choices: tuple[Choice, ...]
    commitment_choices: tuple[Choice, ...]
    items: tuple[AreaItem, ...]  # 20件、領域ごとに5件、AREASの順


# 05_質問・コンテンツ設計2.2「右にいくほどポジティブ」
_SATISFACTION_CHOICES_V1 = (
    Choice(0, "満たされていない"),
    Choice(1, "あまり満たされていない"),
    Choice(2, "どちらとも言えない"),
    Choice(3, "まあ満たされている"),
    Choice(4, "満たされている"),
)

# 05_質問・コンテンツ設計2.4「充足感と向きを揃え、下にいくほどポジティブ」
_COMMITMENT_CHOICES_V1 = (
    Choice(0, "まだこれからのところ"),
    Choice(1, "あまり動けていない"),
    Choice(2, "動けている時と、そうでない時がある"),
    Choice(3, "少し動けている"),
    Choice(4, "しっかり動けている"),
)

# 05_質問・コンテンツ設計2.3
_ITEMS_V1 = (
    AreaItem("CAREER_FULFILLMENT", CAREER, "仕事のやりがい"),
    AreaItem("CAREER_GROWTH", CAREER, "スキルや成長の実感"),
    AreaItem("CAREER_OUTLOOK", CAREER, "今後のキャリアの見通し"),
    AreaItem("CAREER_COMPENSATION", CAREER, "収入や待遇"),
    AreaItem("CAREER_WORK_STYLE", CAREER, "働き方や時間の使い方"),
    AreaItem("FINANCIAL_SAVINGS", FINANCIAL, "貯蓄の状況"),
    AreaItem("FINANCIAL_INCOME", FINANCIAL, "収入の水準"),
    AreaItem("FINANCIAL_SPENDING", FINANCIAL, "支出の把握とコントロール"),
    AreaItem("FINANCIAL_ASSET_BUILDING", FINANCIAL, "将来に向けた資産形成"),
    AreaItem("FINANCIAL_BURDEN", FINANCIAL, "生活費や返済の負担"),
    AreaItem("PHYSICAL_SLEEP", PHYSICAL, "睡眠"),
    AreaItem("PHYSICAL_EXERCISE", PHYSICAL, "運動する習慣"),
    AreaItem("PHYSICAL_DIET", PHYSICAL, "食事"),
    AreaItem("PHYSICAL_RECOVERY", PHYSICAL, "体調や疲れのとれ方"),
    AreaItem("PHYSICAL_BODY", PHYSICAL, "体重や体型"),
    AreaItem("SOCIAL_CONFIDANT", SOCIAL, "気軽に話せる相手がいること"),
    AreaItem("SOCIAL_FAMILY", SOCIAL, "家族やパートナーとの関係"),
    AreaItem("SOCIAL_FRIENDS", SOCIAL, "友人と過ごす時間"),
    AreaItem("SOCIAL_OUTSIDE_WORK", SOCIAL, "職場以外のつながり"),
    AreaItem("SOCIAL_SUPPORT", SOCIAL, "頼れる人がいるという安心感"),
)

QUESTION_SETS: dict[str, QuestionSet] = {
    "2026-08-v1": QuestionSet(
        version="2026-08-v1",
        satisfaction_prompt="{area}について、それぞれ今どのくらい満たされていますか？",
        commitment_prompt="{area}をより良くするために、いま動けていますか？",
        satisfaction_choices=_SATISFACTION_CHOICES_V1,
        commitment_choices=_COMMITMENT_CHOICES_V1,
        items=_ITEMS_V1,
    ),
}

CURRENT_QUESTION_SET_VERSION = "2026-08-v1"


def get_question_set(version: str) -> QuestionSet:
    """`assessment.question_set_version`からその時点の質問定義を復元する(08_データモデル1.2)。"""
    return QUESTION_SETS[version]
