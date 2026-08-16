import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import S31View from "./S-31.vue";
import { usePurposeChoicesStore } from "../stores/purposeChoices";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));

async function answerAllQuestions(wrapper: ReturnType<typeof mount>): Promise<void> {
  await wrapper.findAll(".chip-multi-select__chip")[0]?.trigger("click");
  await wrapper.findAll(".checkbox-choice-selector__input")[0]?.setValue(true);
  await wrapper.findAll(".stacked-choice-selector__input")[2]?.setValue();
}

describe("S-31", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    push.mockReset();
  });

  it("案内文と3問すべてを表示する", () => {
    const wrapper = mount(S31View);

    expect(wrapper.text()).toContain("3〜5年後のあなたについて、いくつか教えてください。まだ決まっていなくて大丈夫です。");
    expect(wrapper.text()).toContain("これからの3〜5年で、大切にしたいことは？");
    expect(wrapper.findAll(".chip-multi-select__chip")).toHaveLength(12);
    expect(wrapper.text()).toContain("満たされていると感じるのは、どんなときですか？");
    expect(wrapper.findAll(".checkbox-choice-selector__option")).toHaveLength(8);
    expect(wrapper.text()).toContain("3〜5年後、どんな毎日を送っていたいですか？");
    expect(wrapper.findAll(".stacked-choice-selector__option")).toHaveLength(6);
  });

  it("ヘッダーに戻る・中断のいずれも置かない", () => {
    const wrapper = mount(S31View);

    expect(wrapper.find(".app-header-flow__nav").exists()).toBe(false);
  });

  it("未回答があるあいだ「次へ」は無効で、補足が表示される", () => {
    const wrapper = mount(S31View);

    expect(wrapper.find("button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("すべて選ぶと、次に進めます");
  });

  it("3問すべてに回答すると「次へ」が有効になる", async () => {
    const wrapper = mount(S31View);

    await answerAllQuestions(wrapper);

    expect(wrapper.find("button[disabled]").exists()).toBe(false);
  });

  it("「次へ」を押すと回答がstoreに記録され、S-32へ遷移する", async () => {
    const wrapper = mount(S31View);
    const store = usePurposeChoicesStore();

    await answerAllQuestions(wrapper);
    await wrapper.find(".s31__cta button").trigger("click");

    expect(store.values).toEqual(["GROWTH"]);
    expect(store.fulfillingMoments).toEqual(["HELPED_SOMEONE"]);
    expect(store.idealDailyLife).toBe("HAVING_OPTIONS");
    expect(push).toHaveBeenCalledWith("/s-32");
  });

  it("価値観は3つを超えて選べない(4つめのチップが無効になる)", async () => {
    const wrapper = mount(S31View);
    const chips = wrapper.findAll(".chip-multi-select__chip");

    await chips[0]?.trigger("click");
    await chips[1]?.trigger("click");
    await chips[2]?.trigger("click");

    const updatedChips = wrapper.findAll(".chip-multi-select__chip");
    expect(updatedChips[3]?.attributes("disabled")).toBeDefined();
  });
});
