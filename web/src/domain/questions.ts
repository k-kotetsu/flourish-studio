/**
 * 選択式(S-12)の質問マスタ。05_質問・コンテンツ設計2章。
 * S-12・S-14の入力はクライアント保持のみでサーバーに問い合わせないため(09_API設計3章)、
 * `api/app/domain/questions.py` の内容をこちらにも複製する。
 * 文言を変えるときは両方に新しいバージョンを追加し、既存キーは書き換えない。
 */

export const CAREER = "CAREER";
export const FINANCIAL = "FINANCIAL";
export const PHYSICAL = "PHYSICAL";
export const SOCIAL = "SOCIAL";
export const AREAS = [CAREER, FINANCIAL, PHYSICAL, SOCIAL] as const;
export type Area = (typeof AREAS)[number];

export const SATISFACTION = "SATISFACTION";
export const COMMITMENT = "COMMITMENT";
export type QuestionKind = typeof SATISFACTION | typeof COMMITMENT;

export interface Choice {
  readonly score: number;
  readonly label: string;
}

export interface AreaItem {
  readonly code: string;
  readonly area: Area;
  readonly label: string;
}

export interface QuestionSet {
  readonly version: string;
  readonly satisfactionPrompt: string;
  readonly commitmentPrompt: string;
  readonly satisfactionChoices: readonly Choice[];
  readonly commitmentChoices: readonly Choice[];
  readonly items: readonly AreaItem[]; // 20件、領域ごとに5件、AREASの順
}

// 05_質問・コンテンツ設計2.2「右にいくほどポジティブ」
const SATISFACTION_CHOICES_V1: readonly Choice[] = [
  { score: 0, label: "満たされていない" },
  { score: 1, label: "あまり満たされていない" },
  { score: 2, label: "どちらとも言えない" },
  { score: 3, label: "まあ満たされている" },
  { score: 4, label: "満たされている" },
];

// 05_質問・コンテンツ設計2.4「充足感と向きを揃え、下にいくほどポジティブ」
const COMMITMENT_CHOICES_V1: readonly Choice[] = [
  { score: 0, label: "まだこれからのところ" },
  { score: 1, label: "あまり動けていない" },
  { score: 2, label: "動けている時と、そうでない時がある" },
  { score: 3, label: "少し動けている" },
  { score: 4, label: "しっかり動けている" },
];

// 05_質問・コンテンツ設計2.3
const ITEMS_V1: readonly AreaItem[] = [
  { code: "CAREER_FULFILLMENT", area: CAREER, label: "仕事のやりがい" },
  { code: "CAREER_GROWTH", area: CAREER, label: "スキルや成長の実感" },
  { code: "CAREER_OUTLOOK", area: CAREER, label: "今後のキャリアの見通し" },
  { code: "CAREER_COMPENSATION", area: CAREER, label: "収入や待遇" },
  { code: "CAREER_WORK_STYLE", area: CAREER, label: "働き方や時間の使い方" },
  { code: "FINANCIAL_SAVINGS", area: FINANCIAL, label: "貯蓄の状況" },
  { code: "FINANCIAL_INCOME", area: FINANCIAL, label: "収入の水準" },
  { code: "FINANCIAL_SPENDING", area: FINANCIAL, label: "支出の把握とコントロール" },
  { code: "FINANCIAL_ASSET_BUILDING", area: FINANCIAL, label: "将来に向けた資産形成" },
  { code: "FINANCIAL_BURDEN", area: FINANCIAL, label: "生活費や返済の負担" },
  { code: "PHYSICAL_SLEEP", area: PHYSICAL, label: "睡眠" },
  { code: "PHYSICAL_EXERCISE", area: PHYSICAL, label: "運動する習慣" },
  { code: "PHYSICAL_DIET", area: PHYSICAL, label: "食事" },
  { code: "PHYSICAL_RECOVERY", area: PHYSICAL, label: "体調や疲れのとれ方" },
  { code: "PHYSICAL_BODY", area: PHYSICAL, label: "体重や体型" },
  { code: "SOCIAL_CONFIDANT", area: SOCIAL, label: "気軽に話せる相手がいること" },
  { code: "SOCIAL_FAMILY", area: SOCIAL, label: "家族やパートナーとの関係" },
  { code: "SOCIAL_FRIENDS", area: SOCIAL, label: "友人と過ごす時間" },
  { code: "SOCIAL_OUTSIDE_WORK", area: SOCIAL, label: "職場以外のつながり" },
  { code: "SOCIAL_SUPPORT", area: SOCIAL, label: "頼れる人がいるという安心感" },
];

export const QUESTION_SETS: Readonly<Record<string, QuestionSet>> = {
  "2026-08-v1": {
    version: "2026-08-v1",
    satisfactionPrompt: "{area}について、それぞれ今どのくらい満たされていますか？",
    commitmentPrompt: "{area}をより良くするために、いま動けていますか？",
    satisfactionChoices: SATISFACTION_CHOICES_V1,
    commitmentChoices: COMMITMENT_CHOICES_V1,
    items: ITEMS_V1,
  },
};

export const CURRENT_QUESTION_SET_VERSION = "2026-08-v1";

/** `assessment.question_set_version` からその時点の質問定義を復元する。 */
export function getQuestionSet(version: string): QuestionSet {
  const set = QUESTION_SETS[version];
  if (!set) {
    throw new Error(`unknown question set version: ${version}`);
  }
  return set;
}

export function itemsForArea(set: QuestionSet, area: Area): AreaItem[] {
  return set.items.filter((item) => item.area === area);
}

/** 画面表示用の領域メタ。en/jpは05_質問・コンテンツ設計2.3の見出し、introLabelとslugは06_ワイヤーフレーム(mockup.html AREAS)に合わせる。 */
export interface AreaMeta {
  readonly area: Area;
  readonly en: string;
  readonly jp: string;
  readonly introLabel: string;
  readonly slug: string;
}

export const AREA_META: Readonly<Record<Area, AreaMeta>> = {
  CAREER: { area: CAREER, en: "Career", jp: "仕事・働き方", introLabel: "仕事や働き方", slug: "career" },
  FINANCIAL: { area: FINANCIAL, en: "Financial", jp: "お金・生活設計", introLabel: "お金や生活のこと", slug: "financial" },
  PHYSICAL: { area: PHYSICAL, en: "Physical", jp: "健康・生活習慣", introLabel: "からだや生活習慣", slug: "physical" },
  SOCIAL: { area: SOCIAL, en: "Social", jp: "人との関係", introLabel: "人との関わり", slug: "social" },
};

export function areaFromSlug(slug: string): Area | null {
  const found = AREAS.find((area) => AREA_META[area].slug === slug);
  return found ?? null;
}
