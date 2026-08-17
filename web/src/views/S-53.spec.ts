import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S53View from "./S-53.vue";
import { generateAreaProposals } from "../api/areaProposals";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";
import { useAreaProposalsStore } from "../stores/areaProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/areaProposals", () => ({
  generateAreaProposals: vi.fn(),
}));

const PROPOSALS = [
  { direction: "DEEPEN" as const, label: "今の場所で深める", ideal_state: "…できている。" },
  { direction: "CHANGE" as const, label: "やり方を変える", ideal_state: "…見つかっている。" },
  { direction: "EXPAND" as const, label: "外に出る", ideal_state: "…持てている。" },
];

function completeDialogue(): void {
  const choicesStore = useAreaChoicesStore();
  choicesStore.setAnswers({
    area: "CAREER",
    changeItemCode: "CAREER_OUTLOOK",
    values: ["CAREER_VALUE_GROWTH"],
    positions: ["CAREER_POSITION_GROWTH"],
  });
  const dialogueStore = useAreaDialogueStore();
  dialogueStore.addMessage({ role: "AI", body: "問い1" });
  dialogueStore.addMessage({ role: "USER", body: "回答1" });
  dialogueStore.addMessage({ role: "AI", body: "問い2" });
  dialogueStore.addMessage({ role: "USER", body: "回答2" });
  dialogueStore.setRemaining(0);
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(generateAreaProposals).mockReset();
});

describe("S-53", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S53View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
    expect(generateAreaProposals).not.toHaveBeenCalled();
  });

  it("対話が完了していなければ同じ領域のS-52へ差し戻す", async () => {
    mount(S53View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-52/career");
    expect(generateAreaProposals).not.toHaveBeenCalled();
  });

  it("画面到達時に3案生成を呼び、成功したら結果を保存して同じ領域のS-54へ遷移する", async () => {
    completeDialogue();
    vi.mocked(generateAreaProposals).mockResolvedValue({
      proposals: PROPOSALS,
      safety_flag: false,
    });

    mount(S53View);
    await flushPromises();

    expect(generateAreaProposals).toHaveBeenCalledOnce();
    expect(push).toHaveBeenCalledWith("/s-54/career");
    const proposalsStore = useAreaProposalsStore();
    expect(proposalsStore.proposals).toEqual(PROPOSALS);
  });

  it("失敗したら同じ画面の中身がエラー表示に入れ替わる(別画面へ遷移しない)", async () => {
    completeDialogue();
    vi.mocked(generateAreaProposals).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S53View);
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("うまく候補を作れませんでした");
    expect(wrapper.text()).toContain("ここまでのお話は、ちゃんと残っています");
  });

  it("「もう一度やってみる」を押したときだけ再試行する(自動リトライしない)", async () => {
    completeDialogue();
    vi.mocked(generateAreaProposals).mockRejectedValueOnce(new Error("provider error"));
    vi.mocked(generateAreaProposals).mockResolvedValueOnce({
      proposals: PROPOSALS,
      safety_flag: false,
    });

    const wrapper = mount(S53View);
    await flushPromises();
    expect(generateAreaProposals).toHaveBeenCalledOnce();

    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(generateAreaProposals).toHaveBeenCalledTimes(2);
    expect(push).toHaveBeenCalledWith("/s-54/career");
  });

  it("「対話に戻る」で同じ領域のS-52へ戻す", async () => {
    completeDialogue();
    vi.mocked(generateAreaProposals).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S53View);
    await flushPromises();

    const buttons = wrapper.findAll("button");
    await buttons[buttons.length - 1]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-52/career");
  });
});
