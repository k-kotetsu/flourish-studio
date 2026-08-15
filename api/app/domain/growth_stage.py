"""成長段階(種/芽/苗/木)。08_データモデル9章`GrowthStage`。

コミット度(事前計算、`assessment_precompute`)と言語化度(AI判定)の両方が、
この同じ4段階を共有する。
"""

SEED = "SEED"
SPROUT = "SPROUT"
SEEDLING = "SEEDLING"
TREE = "TREE"
GROWTH_STAGES = (SEED, SPROUT, SEEDLING, TREE)
