/**
 * S-51(領域：選択式質問)の質問マスタ。05_質問・コンテンツ設計9.2。
 * S-51の入力はクライアント保持のみでサーバーに問い合わせないため(04_画面設計 screen-list.md S-51「保存: しない」)、
 * ここに文言を持つ。文言を変えるときは新しいバージョンを追加し、既存のcodeは書き換えない。
 *
 * Q1(いちばん変えたい項目)はS-12と同じ5項目(`questions.ts`のAreaItem)をそのまま使うため、
 * ここには持たない。Q2(大切にしたいこと)・Q3(人生の中での位置づけ)は領域ごとに文言・選択肢が
 * 異なる(9.2)ため、領域をキーに持つ。
 *
 * codeはドキュメントにない実装上の識別子(S-12のAreaItem.code、S-31のPurposeChoiceOptionと同じ考え方)。
 * 選択肢自体の文言・順序はdocs/05_質問・コンテンツ設計9.2、docs/06_ワイヤーフレーム/mockup.html s51()の記載をそのまま踏襲した。
 */
import { CAREER, FINANCIAL, PHYSICAL, SOCIAL, type Area } from "./questions";

export interface AreaChoiceOption {
  readonly code: string;
  readonly label: string;
}

export const AREA_VALUES_PROMPT: Readonly<Record<Area, string>> = {
  CAREER: "これからの仕事で、特に大切にしたいことは？",
  FINANCIAL: "これからのお金について、特に大切にしたいことは？",
  PHYSICAL: "これからのからだについて、特に大切にしたいことは？",
  SOCIAL: "これからの人との関係で、特に大切にしたいことは？",
};

export const AREA_POSITION_PROMPT: Readonly<Record<Area, string>> = {
  CAREER: "これから、仕事は人生の中でどんな存在であってほしい？",
  FINANCIAL: "これから、お金は人生の中でどんな存在であってほしい？",
  PHYSICAL: "これから、からだは人生の中でどんな存在であってほしい？",
  SOCIAL: "これから、人とのつながりは人生の中でどんな存在であってほしい？",
};

const CAREER_VALUES_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "CAREER_VALUE_GROWTH", label: "自分の成長を実感できること" },
  { code: "CAREER_VALUE_CONTRIBUTION", label: "誰かの役に立っている手ごたえ" },
  { code: "CAREER_VALUE_RECOGNITION", label: "正当に評価されること" },
  { code: "CAREER_VALUE_RELATIONSHIPS", label: "一緒に働く人との相性" },
  { code: "CAREER_VALUE_AUTONOMY", label: "自分で決められる裁量があること" },
  { code: "CAREER_VALUE_STABILITY", label: "安定して続けられること" },
  { code: "CAREER_VALUE_INCOME_GROWTH", label: "収入が上がっていくこと" },
  { code: "CAREER_VALUE_CHALLENGE", label: "新しいことに挑戦できること" },
  { code: "CAREER_VALUE_EXPERTISE", label: "専門性を深められること" },
  { code: "CAREER_VALUE_WORK_LIFE_BALANCE", label: "生活を圧迫しない働き方であること" },
];

const CAREER_POSITION_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "CAREER_POSITION_EXPRESSION", label: "自分を表現する場であってほしい" },
  { code: "CAREER_POSITION_MEANS", label: "生活を支える手段であればいい" },
  { code: "CAREER_POSITION_GROWTH", label: "成長し続けられる場であってほしい" },
  { code: "CAREER_POSITION_CONNECTION", label: "人とのつながりが生まれる場であってほしい" },
  { code: "CAREER_POSITION_TESTING_GROUND", label: "自分の力を試せる場であってほしい" },
  { code: "CAREER_POSITION_LOW_STRESS", label: "心をすり減らさない場であってほしい" },
  { code: "CAREER_POSITION_CENTER", label: "人生の中心にあってほしい" },
  { code: "CAREER_POSITION_PERIPHERAL", label: "人生の一部くらいの距離でいてほしい" },
  { code: "CAREER_POSITION_PRIDE", label: "誇りを持てる場であってほしい" },
  { code: "CAREER_POSITION_FLEXIBLE", label: "いつでも変えられる選択肢のひとつでいてほしい" },
];

const FINANCIAL_VALUES_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "FINANCIAL_VALUE_REDUCE_ANXIETY", label: "将来の不安を減らすこと" },
  { code: "FINANCIAL_VALUE_MAINTAIN_QUALITY", label: "今の生活の質を落とさないこと" },
  { code: "FINANCIAL_VALUE_AUTONOMY", label: "使い道を自分で決められること" },
  { code: "FINANCIAL_VALUE_PREPAREDNESS", label: "想定外の出来事に備えられること" },
  { code: "FINANCIAL_VALUE_INCOME_GROWTH", label: "収入を増やしていくこと" },
  { code: "FINANCIAL_VALUE_ORGANIZATION", label: "無駄をなくして整えること" },
  { code: "FINANCIAL_VALUE_FOR_LOVED_ONES", label: "大切な人のために使えること" },
  { code: "FINANCIAL_VALUE_LESS_WORRY", label: "お金のことで悩む時間を減らすこと" },
  { code: "FINANCIAL_VALUE_NO_COMPROMISE", label: "やりたいことを諦めずに済むこと" },
  { code: "FINANCIAL_VALUE_ASSET_BUILDING", label: "資産を計画的に増やしていくこと" },
];

const FINANCIAL_POSITION_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "FINANCIAL_POSITION_UNCONSCIOUS", label: "意識せずに済む存在であってほしい" },
  { code: "FINANCIAL_POSITION_OPTIONS", label: "選択肢を広げてくれる存在であってほしい" },
  { code: "FINANCIAL_POSITION_FOUNDATION", label: "安心の土台であってほしい" },
  { code: "FINANCIAL_POSITION_MARGIN", label: "自由に使える余裕があってほしい" },
  { code: "FINANCIAL_POSITION_MEASURE", label: "目標を測るものさしであってほしい" },
  { code: "FINANCIAL_POSITION_SUPPORT_OTHERS", label: "誰かを支えるために使えるものであってほしい" },
  { code: "FINANCIAL_POSITION_ENJOY_GROWING", label: "増やすこと自体を楽しめるものであってほしい" },
  { code: "FINANCIAL_POSITION_SUFFICIENT", label: "生活が回れば十分な存在でいてほしい" },
  { code: "FINANCIAL_POSITION_FUTURE_SELF", label: "将来の自分への仕送りであってほしい" },
  { code: "FINANCIAL_POSITION_NO_ANXIETY", label: "不安の種にならない存在であってほしい" },
];

const PHYSICAL_VALUES_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "PHYSICAL_VALUE_DAILY_ENERGY", label: "毎日を元気に過ごせること" },
  { code: "PHYSICAL_VALUE_RECOVERY", label: "疲れを翌日に持ち越さないこと" },
  { code: "PHYSICAL_VALUE_APPEARANCE", label: "見た目に納得できること" },
  { code: "PHYSICAL_VALUE_LONGEVITY", label: "長く健康でいられること" },
  { code: "PHYSICAL_VALUE_SLEEP", label: "よく眠れること" },
  { code: "PHYSICAL_VALUE_SUSTAINABLE_HABIT", label: "無理のない習慣にできること" },
  { code: "PHYSICAL_VALUE_MOOD_STABILITY", label: "気分が安定していること" },
  { code: "PHYSICAL_VALUE_STAMINA", label: "体力に自信を持てること" },
  { code: "PHYSICAL_VALUE_REDUCE_ILLNESS_ANXIETY", label: "病気の不安を減らすこと" },
  { code: "PHYSICAL_VALUE_ENJOY_MOVEMENT", label: "からだを動かすことを楽しめること" },
];

const PHYSICAL_POSITION_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "PHYSICAL_POSITION_CARE_FREE", label: "何も気にせずにいられる存在であってほしい" },
  { code: "PHYSICAL_POSITION_SUPPORT_GOALS", label: "やりたいことを支えてくれる存在であってほしい" },
  { code: "PHYSICAL_POSITION_SELF_CARE", label: "自分を大事にしている実感になってほしい" },
  { code: "PHYSICAL_POSITION_ENJOY_MAINTAINING", label: "整えること自体が楽しみであってほしい" },
  { code: "PHYSICAL_POSITION_CONFIDENCE", label: "自信の源であってほしい" },
  { code: "PHYSICAL_POSITION_RHYTHM", label: "生活のリズムを作るものであってほしい" },
  { code: "PHYSICAL_POSITION_LONG_TERM", label: "年を重ねても付き合っていける存在であってほしい" },
  { code: "PHYSICAL_POSITION_LIMITER", label: "頑張りすぎを止めてくれる存在であってほしい" },
  { code: "PHYSICAL_POSITION_MOOD_RESET", label: "気分を切り替える手段であってほしい" },
  { code: "PHYSICAL_POSITION_SHARED_ENJOYMENT", label: "誰かと一緒に楽しめるものであってほしい" },
];

const SOCIAL_VALUES_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "SOCIAL_VALUE_EASE", label: "気を使わずにいられること" },
  { code: "SOCIAL_VALUE_RELIABILITY", label: "困ったときに頼れること" },
  { code: "SOCIAL_VALUE_HONESTY", label: "本音で話せること" },
  { code: "SOCIAL_VALUE_ENJOYMENT", label: "一緒にいて楽しいこと" },
  { code: "SOCIAL_VALUE_BEING_USEFUL", label: "相手の力になれること" },
  { code: "SOCIAL_VALUE_NO_FORCING", label: "無理して合わせなくていいこと" },
  { code: "SOCIAL_VALUE_LONGEVITY", label: "長く続いていくこと" },
  { code: "SOCIAL_VALUE_NEW_ENCOUNTERS", label: "新しい出会いがあること" },
  { code: "SOCIAL_VALUE_MUTUAL_RESPECT", label: "お互いを認め合えること" },
  { code: "SOCIAL_VALUE_RESPECT_SOLITUDE", label: "ひとりの時間も尊重されること" },
];

const SOCIAL_POSITION_OPTIONS: readonly AreaChoiceOption[] = [
  { code: "SOCIAL_POSITION_SAFE_HAVEN", label: "安心して戻れる場所であってほしい" },
  { code: "SOCIAL_POSITION_STIMULATION", label: "刺激をくれる存在であってほしい" },
  { code: "SOCIAL_POSITION_SELF_DISCOVERY", label: "自分を知るきっかけであってほしい" },
  { code: "SOCIAL_POSITION_MUTUAL_SUPPORT", label: "支え合える関係であってほしい" },
  { code: "SOCIAL_POSITION_FEW_BUT_DEEP", label: "数は少なくても、濃くありたい" },
  { code: "SOCIAL_POSITION_WIDE_AND_LOOSE", label: "広く、ゆるやかにつながっていたい" },
  { code: "SOCIAL_POSITION_AUTHENTICITY", label: "自分らしくいられる場であってほしい" },
  { code: "SOCIAL_POSITION_LIFE_COMPANION", label: "人生を一緒に歩む存在であってほしい" },
  { code: "SOCIAL_POSITION_AS_NEEDED", label: "必要なときにだけあればいい" },
  { code: "SOCIAL_POSITION_BEING_A_HAVEN", label: "誰かの居場所になれる関係であってほしい" },
];

export const AREA_VALUES_OPTIONS: Readonly<Record<Area, readonly AreaChoiceOption[]>> = {
  [CAREER]: CAREER_VALUES_OPTIONS,
  [FINANCIAL]: FINANCIAL_VALUES_OPTIONS,
  [PHYSICAL]: PHYSICAL_VALUES_OPTIONS,
  [SOCIAL]: SOCIAL_VALUES_OPTIONS,
};

export const AREA_POSITION_OPTIONS: Readonly<Record<Area, readonly AreaChoiceOption[]>> = {
  [CAREER]: CAREER_POSITION_OPTIONS,
  [FINANCIAL]: FINANCIAL_POSITION_OPTIONS,
  [PHYSICAL]: PHYSICAL_POSITION_OPTIONS,
  [SOCIAL]: SOCIAL_POSITION_OPTIONS,
};
