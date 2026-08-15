import { describe, expect, it } from "vitest";
import { GROWTH_STAGES, GROWTH_STAGE_ICONS, GROWTH_STAGE_LABELS } from "./growthStage";

describe("growthStage", () => {
  it("4段階すべてにラベルとアイコンが揃っている", () => {
    expect(GROWTH_STAGES).toEqual(["SEED", "SPROUT", "SEEDLING", "TREE"]);
    for (const stage of GROWTH_STAGES) {
      expect(GROWTH_STAGE_LABELS[stage]).toMatch(/^.$/); // 種/芽/苗/木は1文字
      expect(GROWTH_STAGE_ICONS[stage].viewBox).toBe("0 0 24 24");
      expect(GROWTH_STAGE_ICONS[stage].paths.length).toBeGreaterThan(0);
      for (const d of GROWTH_STAGE_ICONS[stage].paths) {
        expect(d).toMatch(/^M/); // pathは移動コマンドから始まる
      }
    }
  });

  it("4段階とも同じ接地線(x=7〜17, y=20.25)の上に立つ(4つ並べたときの基準線を揃える)", () => {
    for (const stage of GROWTH_STAGES) {
      expect(GROWTH_STAGE_ICONS[stage].paths[0]).toBe("M7 20.25H17");
    }
  });
});
