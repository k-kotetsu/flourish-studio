import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import S12View from "./S-12.vue";
import { useAssessmentAnswersStore } from "../stores/assessmentAnswers";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));

async function answerAllQuestions(wrapper: VueWrapper): Promise<void> {
  const blocks = wrapper.findAll(".s12__question");
  for (const block of blocks) {
    const inputs = block.findAll("input[type=radio]");
    await inputs[inputs.length - 1]?.setValue();
  }
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
});

describe("S-12", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("領域見出しと導入文を表示する", () => {
    const wrapper = mount(S12View);

    expect(wrapper.text()).toContain("Career");
    expect(wrapper.text()).toContain("仕事・働き方");
    expect(wrapper.text()).toContain("右にいくほど、満たされている状態です");
    expect(wrapper.find(".s12__heading svg").exists()).toBe(true); // P7-3: 4領域アイコン
  });

  it("6問(充足感5＋コミット度1)を表示する", () => {
    const wrapper = mount(S12View);

    expect(wrapper.findAll(".s12__question")).toHaveLength(6);
    expect(wrapper.text()).toContain("仕事のやりがい");
    expect(wrapper.text()).toContain("Career をより良くするために、いま動けていますか？");
  });

  it("未回答があるあいだ「次へ」は無効で、補足が表示される", () => {
    const wrapper = mount(S12View);

    expect(wrapper.find("button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("すべて選ぶと、次に進めます");
  });

  it("全6問に回答すると「次へ」が有効になり、補足が消える", async () => {
    const wrapper = mount(S12View);

    await answerAllQuestions(wrapper);

    expect(wrapper.find("button[disabled]").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("すべて選ぶと、次に進めます");
  });

  it("Careerで次へを押すと回答がstoreに記録され、次の領域(Financial)へ遷移する", async () => {
    const wrapper = mount(S12View);
    const store = useAssessmentAnswersStore();

    await answerAllQuestions(wrapper);
    await wrapper.find(".s12__cta button").trigger("click");

    expect(store.scaleAnswers).toHaveLength(6);
    expect(store.scaleAnswers.filter((a) => a.area === "CAREER" && a.question_kind === "SATISFACTION")).toHaveLength(
      5,
    );
    expect(store.scaleAnswers.filter((a) => a.question_kind === "COMMITMENT")).toHaveLength(1);
    expect(push).toHaveBeenCalledWith("/s-12/financial");
  });

  it("Socialで次へを押すとS-13(未実装)へ遷移する", async () => {
    routeParams.area = "social";
    const wrapper = mount(S12View);

    await answerAllQuestions(wrapper);
    await wrapper.find(".s12__cta button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-13");
  });

  it("未知の領域パラメータではS-11へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S12View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-11");
  });

  it("「× 中断」→「やめる」でstoreをリセットし、トップページへ遷移する", async () => {
    const store = useAssessmentAnswersStore();
    store.recordArea("CAREER", [{ area: "CAREER", question_kind: "COMMITMENT", score: 2 }]);

    const wrapper = mount(S12View);
    await wrapper.find(".app-header-flow__nav").trigger("click");
    // InterruptDialogはTeleport(to="body")で描画されるため、document.body側から探す
    const leaveButton = document.body.querySelectorAll(".interrupt-dialog button")[1] as HTMLButtonElement;
    leaveButton.click();
    await flushPromises();

    expect(store.scaleAnswers).toEqual([]);
    expect(push).toHaveBeenCalledWith("/");
    wrapper.unmount();
  });

  it("「× 中断」→「つづける」では遷移せず、ダイアログが閉じる", async () => {
    const wrapper = mount(S12View);
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
