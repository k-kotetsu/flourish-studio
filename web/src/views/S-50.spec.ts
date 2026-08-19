import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import S50View from "./S-50.vue";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));

describe("S-50", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("タイトルと案内文を表示し、戻る・中断のいずれも置かない", () => {
    const wrapper = mount(S50View);

    expect(wrapper.text()).toContain("Flourish Map");
    expect(wrapper.text()).toContain("どこから");
    expect(wrapper.text()).toContain("育てはじめますか");
    expect(wrapper.text()).toContain("ひとつだけ選んでください。あとから他の領域も作れます。");
    expect(wrapper.find(".app-header-hub button").exists()).toBe(false);
  });

  it("4領域をAREASの並び順(Career→Financial→Physical→Social)で同列に表示する", () => {
    const wrapper = mount(S50View);
    const cards = wrapper.findAll(".s50__card");

    expect(cards).toHaveLength(4);
    expect(cards.map((c) => c.text())).toEqual([
      "Career仕事・働き方",
      "Financialお金・生活設計",
      "Physical健康・生活習慣",
      "Social人との関係",
    ]);
    expect(cards.every((c) => c.find("svg").exists())).toBe(true); // P7-3: 4領域アイコン
  });

  it("推奨・優先度を示すバッジやラベルを一切出さない", () => {
    const wrapper = mount(S50View);

    expect(wrapper.text()).not.toContain("おすすめ");
    expect(wrapper.text()).not.toContain("人気");
    expect(wrapper.find(".s50__badge").exists()).toBe(false);
  });

  it("領域カードを選ぶとS-51(その領域)へ遷移する", async () => {
    const wrapper = mount(S50View);

    await wrapper.findAll(".s50__card")[2]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-51/physical");
  });

  it("「あとで」を押すとS-41へ遷移する", async () => {
    const wrapper = mount(S50View);

    await wrapper.find(".s50__skip").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-41");
  });
});
