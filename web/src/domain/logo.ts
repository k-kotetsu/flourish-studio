/**
 * ロゴマーク(P7-3、定義書19章 未決#4「ロゴとサービス名のロックアップ」)。
 * `docs/06_ワイヤーフレーム/mockup.html`の`ICON_FLOURISH`(双葉のモチーフ)をロゴマークとして採用した。
 * 成長段階アイコン(`growthStage.ts`)・4領域アイコン(`areaIcons.ts`)と同じ線画スタイル
 * (24pxグリッド、線幅1.6px、線端・接合部を丸める、`currentColor`)で、サービス名「Flourish」が
 * 表す成長・繁茂のイメージをそのまま図形化している。
 * ロゴマーク単体では意味を持たないため、常に「Flourish Studio」の文字と組み合わせる
 * ロックアップとして使う(表示は`AppLogo.vue`)。
 */
export const LOGO_MARK_VIEW_BOX = "0 0 24 24";

export const LOGO_MARK_PATHS: readonly string[] = [
  "M12 21V10",
  "M12 13c0-4-3-6.5-7-6.5 0 4 3 6.5 7 6.5z",
  "M12 15c0-4 3-6.5 7-6.5 0 4-3 6.5-7 6.5z",
  "M8 21h8",
];

export const SERVICE_NAME = "Flourish Studio";
