/**
 * 成長段階(種・芽・苗・木)。08_データモデル9章`GrowthStage`。
 * 言語化度(articulation_stage)・コミット度(commitment_stage)が共有する同じ4段階
 * (`api/app/domain/growth_stage.py`と同じ並び)。
 */

export const SEED = "SEED";
export const SPROUT = "SPROUT";
export const SEEDLING = "SEEDLING";
export const TREE = "TREE";
export const GROWTH_STAGES = [SEED, SPROUT, SEEDLING, TREE] as const;
export type GrowthStage = (typeof GROWTH_STAGES)[number];

export const GROWTH_STAGE_LABELS: Readonly<Record<GrowthStage, string>> = {
  SEED: "種",
  SPROUT: "芽",
  SEEDLING: "苗",
  TREE: "木",
};

/**
 * 成長段階の線画アイコン(P2-10、`07_デザイン原則`7.6)。24pxグリッド、線幅1.6px、
 * 線端・接合部を丸める、塗りつぶしなし。既製セットに4段階が揃った組がないため描き起こした。
 * 4つとも同じ接地線(x=7〜17, y=20.25)の上に立たせ、種(接地のみ・幹なし)→芽(短い幹＋小さな葉)→
 * 苗(高い幹＋大きい葉＋伸びる先端)→木(最も高い幹＋丸い樹冠)と、高さと複雑さが単調に増える
 * ことで、4つ並べたときに成長の連続として読み取れるようにした。
 * 表示側はこの`paths`を`<path :d="..." fill="none" stroke="currentColor" stroke-width="1.6"
 * stroke-linecap="round" stroke-linejoin="round" />`として並べて使う(P2-11)。
 */
export interface GrowthStageIcon {
  readonly viewBox: string;
  readonly paths: readonly string[];
}

export const GROWTH_STAGE_ICONS: Readonly<Record<GrowthStage, GrowthStageIcon>> = {
  SEED: {
    viewBox: "0 0 24 24",
    paths: [
      "M7 20.25H17",
      "M12 20C9.8 20 8 18 8 15.3C8 12.2 9.8 9.4 12 7.3C14.2 9.4 16 12.2 16 15.3C16 18 14.2 20 12 20Z",
    ],
  },
  SPROUT: {
    viewBox: "0 0 24 24",
    paths: [
      "M7 20.25H17",
      "M12 20V14.6",
      "M12 15.2C12 15.2 9 15.2 8.3 12.2C10.9 12.2 12 13.6 12 15.2Z",
      "M12 16C12 16 15 16 15.7 13C13.1 13 12 14.4 12 16Z",
    ],
  },
  SEEDLING: {
    viewBox: "0 0 24 24",
    paths: [
      "M7 20.25H17",
      "M12 20V9.4",
      "M12 10.4C12 10.4 8 10.4 7.1 6.6C10.4 6.6 12 8.4 12 10.4Z",
      "M12 11.6C12 11.6 16 11.6 16.9 7.8C13.6 7.8 12 9.6 12 11.6Z",
      "M12 9.4L12 7",
    ],
  },
  TREE: {
    viewBox: "0 0 24 24",
    paths: [
      "M7 20.25H17",
      "M12 20V14",
      "M10 20L12 17.6",
      "M14 20L12 17.6",
      "M6.4 12.2C6.4 8.9 8.9 6.3 12 6.3C15.1 6.3 17.6 8.9 17.6 12.2C17.6 15 15.1 17 12 17C8.9 17 6.4 15 6.4 12.2Z",
    ],
  },
};
