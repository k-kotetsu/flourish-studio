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
