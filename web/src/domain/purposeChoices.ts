/**
 * S-31(ありたい姿：選択式3問)の質問マスタ。05_質問・コンテンツ設計6章。
 * S-31の入力はクライアント保持のみでサーバーに問い合わせないため(04_画面設計 screen-list.md S-31「保存: しない」)、
 * ここに文言を持つ。文言を変えるときは新しいバージョンを追加し、既存のcodeは書き換えない。
 *
 * codeはドキュメントにない実装上の識別子(S-12のAreaItem.codeと同じ考え方)。
 * 選択肢自体の文言・順序はdocs/05_質問・コンテンツ設計6章、docs/06_ワイヤーフレーム/mockup.html s31()の記載をそのまま踏襲した。
 */

export interface PurposeChoiceOption {
  readonly code: string;
  readonly label: string;
}

/** Q1: これからの3〜5年で、大切にしたいことは？（3つまで選択） */
export const VALUES_OPTIONS: readonly PurposeChoiceOption[] = [
  { code: "GROWTH", label: "成長" },
  { code: "STABILITY", label: "安定" },
  { code: "FREEDOM", label: "自由" },
  { code: "CONNECTION", label: "つながり" },
  { code: "CHALLENGE", label: "挑戦" },
  { code: "CONTRIBUTION", label: "貢献" },
  { code: "AUTHENTICITY", label: "自分らしさ" },
  { code: "INTEGRITY", label: "誠実さ" },
  { code: "LEARNING", label: "学び" },
  { code: "HEALTH", label: "健康" },
  { code: "MARGIN", label: "余白" },
  { code: "FAMILY", label: "家族" },
];

export const VALUES_MAX_SELECTION = 3;

/** Q2: 満たされていると感じるのは、どんなときですか？（複数選択） */
export const FULFILLING_MOMENT_OPTIONS: readonly PurposeChoiceOption[] = [
  { code: "HELPED_SOMEONE", label: "誰かの役に立てたと感じたとき" },
  { code: "NEW_ABILITY", label: "新しいことができるようになったとき" },
  { code: "SELF_DETERMINED", label: "自分で決められたと感じたとき" },
  { code: "TIME_WITH_LOVED_ONES", label: "大切な人と過ごしているとき" },
  { code: "SETTLED_LIFE", label: "落ち着いた生活が送れているとき" },
  { code: "FOCUSED", label: "集中して何かに取り組めたとき" },
  { code: "RECOGNIZED", label: "認められたと感じたとき" },
  { code: "UNSURE", label: "まだよくわからない" },
];

/** Q3: 3〜5年後、どんな毎日を送っていたいですか？（1つ選択） */
export const IDEAL_DAILY_LIFE_OPTIONS: readonly PurposeChoiceOption[] = [
  { code: "EXTENSION_OF_NOW", label: "今の延長線上で、より満足できている" },
  { code: "DIFFERENT_PLACE_OR_STYLE", label: "今とは違う場所や働き方をしている" },
  { code: "HAVING_OPTIONS", label: "選択肢を持てる状態になっている" },
  { code: "TIME_FOR_LOVED_ONES", label: "大切な人との時間が確保できている" },
  { code: "ROOM_TO_BREATHE", label: "心身に余裕がある" },
  { code: "CANT_IMAGINE_YET", label: "まだ想像がつかない" },
];
