import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import S51View from "./S-51.vue";
import { getCurrentPurpose } from "../api/purposes";
import { ApiError } from "../api/client";
import { useAreaChoicesStore } from "../stores/areaChoices";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/purposes", () => ({
  getCurrentPurpose: vi.fn(),
}));

const PURPOSE = {
  version: 1,
  statement: "自分で選んだと言えることを積み重ねて生きていきたい。",
  selected_direction: "SELF" as const,
  selected_label: "自分の納得を軸に",
  created_at: "2026-08-07T05:00:00Z",
};

async function answerAllQuestions(wrapper: VueWrapper): Promise<void> {
  const radios = wrapper.findAll(".stacked-choice-selector__input");
  await radios[radios.length - 1]?.setValue();
  const checkboxGroups = wrapper.findAll(".checkbox-choice-selector");
  await checkboxGroups[0]?.findAll("input[type=checkbox]")[0]?.setValue(true);
  await checkboxGroups[1]?.findAll("input[type=checkbox]")[0]?.setValue(true);
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(getCurrentPurpose).mockReset();
});

describe("S-51", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("領域名(見出し)とありたい姿を表示する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();

    expect(wrapper.text()).toContain("Career");
    expect(wrapper.text()).toContain(PURPOSE.statement);
  });

  it("3問(Q1単一選択・Q2/Q3各10項目の複数選択)を表示する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();

    expect(wrapper.text()).toContain("Careerの中で、3〜5年後にいちばん変わっていてほしいのはどれですか？");
    expect(wrapper.findAll(".stacked-choice-selector__option")).toHaveLength(5);
    expect(wrapper.text()).toContain("これからの仕事で、特に大切にしたいことは？");
    expect(wrapper.text()).toContain("これから、仕事は人生の中でどんな存在であってほしい？");
    const checkboxGroups = wrapper.findAll(".checkbox-choice-selector");
    expect(checkboxGroups[0]?.findAll(".checkbox-choice-selector__option")).toHaveLength(10);
    expect(checkboxGroups[1]?.findAll(".checkbox-choice-selector__option")).toHaveLength(10);
  });

  it("領域ごとにQ2・Q3の文言と選択肢が変わる(Financial)", async () => {
    routeParams.area = "financial";
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();

    expect(wrapper.text()).toContain("Financialの中で、3〜5年後にいちばん変わっていてほしいのはどれですか？");
    expect(wrapper.text()).toContain("これからのお金について、特に大切にしたいことは？");
    expect(wrapper.text()).toContain("将来の不安を減らすこと");
  });

  it("取得に失敗したらエラーを表示し、設問は表示しない", async () => {
    vi.mocked(getCurrentPurpose).mockRejectedValue(new ApiError(401, "UNAUTHENTICATED", "no session"));
    const wrapper = mount(S51View);
    await flushPromises();

    expect(wrapper.find(".s51__error").exists()).toBe(true);
    expect(wrapper.findAll(".s51__question")).toHaveLength(0);
  });

  it("未回答があるあいだ「次へ」は無効で、補足が表示される", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();

    expect(wrapper.find("button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("すべて選ぶと、次に進めます");
  });

  it("3問すべてに回答すると「次へ」が有効になる", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();

    await answerAllQuestions(wrapper);

    expect(wrapper.find("button[disabled]").exists()).toBe(false);
  });

  it("「次へ」を押すと回答がstoreに記録され、S-52(同じ領域)へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    const store = useAreaChoicesStore();
    await flushPromises();

    await answerAllQuestions(wrapper);
    await wrapper.find(".s51__cta button").trigger("click");

    expect(store.area).toBe("CAREER");
    expect(store.changeItemCode).toBe("CAREER_WORK_STYLE");
    expect(store.values).toEqual(["CAREER_VALUE_GROWTH"]);
    expect(store.positions).toEqual(["CAREER_POSITION_EXPRESSION"]);
    expect(push).toHaveBeenCalledWith("/s-52/career");
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S51View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("「× 中断」→「やめる」でstoreをリセットし、S-41へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const store = useAreaChoicesStore();
    store.setAnswers({ area: "CAREER", changeItemCode: "CAREER_GROWTH", values: ["CAREER_VALUE_GROWTH"], positions: [] });

    const wrapper = mount(S51View);
    await flushPromises();
    await wrapper.find(".app-header-flow__nav").trigger("click");
    const leaveButton = document.body.querySelectorAll(".interrupt-dialog button")[1] as HTMLButtonElement;
    leaveButton.click();
    await flushPromises();

    expect(store.area).toBeNull();
    expect(push).toHaveBeenCalledWith("/s-41");
    wrapper.unmount();
  });

  it("「× 中断」→「つづける」では遷移せず、ダイアログが閉じる", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S51View);
    await flushPromises();
    await wrapper.find(".app-header-flow__nav").trigger("click");
    expect(document.body.querySelector(".interrupt-dialog")).not.toBeNull();

    const continueButton = document.body.querySelectorAll(".interrupt-dialog button")[0] as HTMLButtonElement;
    continueButton.click();
    await flushPromises();

    expect(document.body.querySelector(".interrupt-dialog")).toBeNull();
    expect(push).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
