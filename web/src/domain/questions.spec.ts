import { describe, expect, it } from "vitest";
import {
  AREAS,
  AREA_META,
  CURRENT_QUESTION_SET_VERSION,
  QUESTION_SETS,
  areaFromSlug,
  getQuestionSet,
  itemsForArea,
} from "./questions";

describe("questions", () => {
  it("CURRENT_QUESTION_SET_VERSION がQUESTION_SETSに存在する", () => {
    expect(QUESTION_SETS[CURRENT_QUESTION_SET_VERSION]).toBeDefined();
  });

  it("未知のバージョンを渡すとエラーになる", () => {
    expect(() => getQuestionSet("not-a-version")).toThrow();
  });

  it("20項目が5件×4領域で重複なく揃う", () => {
    const set = getQuestionSet(CURRENT_QUESTION_SET_VERSION);
    expect(set.items).toHaveLength(20);

    const codes = new Set(set.items.map((item) => item.code));
    expect(codes.size).toBe(20);

    for (const area of AREAS) {
      expect(itemsForArea(set, area)).toHaveLength(5);
    }
  });

  it("充足感・コミット度の選択肢は0〜4の5段階で、右/下がポジティブ", () => {
    const set = getQuestionSet(CURRENT_QUESTION_SET_VERSION);

    expect(set.satisfactionChoices.map((c) => c.score)).toEqual([0, 1, 2, 3, 4]);
    expect(set.satisfactionChoices[0].label).toBe("満たされていない");
    expect(set.satisfactionChoices[4].label).toBe("満たされている");

    expect(set.commitmentChoices.map((c) => c.score)).toEqual([0, 1, 2, 3, 4]);
    expect(set.commitmentChoices[0].label).toBe("まだこれからのところ");
    expect(set.commitmentChoices[4].label).toBe("しっかり動けている");
  });

  it("AREA_META は全AREAに対応し、slugが一意", () => {
    const slugs = AREAS.map((area) => AREA_META[area].slug);
    expect(new Set(slugs).size).toBe(AREAS.length);
  });

  it("areaFromSlug は既知のslugを領域に、未知のslugはnullに変換する", () => {
    expect(areaFromSlug("career")).toBe("CAREER");
    expect(areaFromSlug("social")).toBe("SOCIAL");
    expect(areaFromSlug("nope")).toBeNull();
  });
});
