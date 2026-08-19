import { describe, expect, it } from "vitest";
import { AREAS } from "./questions";
import { AREA_ICONS } from "./areaIcons";

describe("areaIcons", () => {
  it("4領域すべてにアイコンが揃っている", () => {
    for (const area of AREAS) {
      const icon = AREA_ICONS[area];
      expect(icon.viewBox).toBe("0 0 24 24");
      expect(icon.elements.length).toBeGreaterThan(0);
    }
  });

  it("領域固有の色を持たない(currentColorのみ。要素に色情報を含まない)", () => {
    for (const area of AREAS) {
      for (const el of AREA_ICONS[area].elements) {
        expect(el).not.toHaveProperty("fill");
        expect(el).not.toHaveProperty("stroke");
      }
    }
  });
});
