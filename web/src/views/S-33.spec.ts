import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S33View from "./S-33.vue";
import { generatePurposeProposals } from "../api/purposeProposals";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/purposeProposals", () => ({
  generatePurposeProposals: vi.fn(),
}));

const PROPOSALS = [
  { direction: "SELF" as const, label: "自分の納得を軸に", statement: "…でありたい。" },
  { direction: "OTHERS" as const, label: "まわりの人とともに", statement: "…でありたい。" },
  { direction: "SOCIETY" as const, label: "もっと広く", statement: "…していきたい。" },
];

function completeDialogue(): void {
  const choicesStore = usePurposeChoicesStore();
  choicesStore.setAnswers({
    values: ["GROWTH"],
    fulfillingMoments: ["SELF_DETERMINED"],
    idealDailyLife: "HAVING_OPTIONS",
  });
  const dialogueStore = usePurposeDialogueStore();
  dialogueStore.addMessage({ role: "AI", body: "問い1" });
  dialogueStore.addMessage({ role: "USER", body: "回答1" });
  dialogueStore.addMessage({ role: "AI", body: "問い2" });
  dialogueStore.addMessage({ role: "USER", body: "回答2" });
  dialogueStore.addMessage({ role: "AI", body: "問い3" });
  dialogueStore.addMessage({ role: "USER", body: "回答3" });
  dialogueStore.setRemaining(0);
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(generatePurposeProposals).mockReset();
});

describe("S-33", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("対話が完了していなければS-31へ差し戻す", async () => {
    mount(S33View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-31");
    expect(generatePurposeProposals).not.toHaveBeenCalled();
  });

  it("画面到達時に3案生成を呼び、成功したら結果を保存してS-34へ遷移する", async () => {
    completeDialogue();
    vi.mocked(generatePurposeProposals).mockResolvedValue({
      proposals: PROPOSALS,
      safety_flag: false,
    });

    mount(S33View);
    await flushPromises();

    expect(generatePurposeProposals).toHaveBeenCalledOnce();
    expect(push).toHaveBeenCalledWith("/s-34");
    const proposalsStore = usePurposeProposalsStore();
    expect(proposalsStore.proposals).toEqual(PROPOSALS);
  });

  it("失敗したら同じ画面の中身がエラー表示に入れ替わる(別画面へ遷移しない)", async () => {
    completeDialogue();
    vi.mocked(generatePurposeProposals).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S33View);
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("うまく候補を作れませんでした");
    expect(wrapper.text()).toContain("ここまでのお話は、ちゃんと残っています");
  });

  it("「もう一度やってみる」を押したときだけ再試行する(自動リトライしない)", async () => {
    completeDialogue();
    vi.mocked(generatePurposeProposals).mockRejectedValueOnce(new Error("provider error"));
    vi.mocked(generatePurposeProposals).mockResolvedValueOnce({
      proposals: PROPOSALS,
      safety_flag: false,
    });

    const wrapper = mount(S33View);
    await flushPromises();
    expect(generatePurposeProposals).toHaveBeenCalledOnce();

    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(generatePurposeProposals).toHaveBeenCalledTimes(2);
    expect(push).toHaveBeenCalledWith("/s-34");
  });

  it("「対話に戻る」でS-32へ戻す", async () => {
    completeDialogue();
    vi.mocked(generatePurposeProposals).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S33View);
    await flushPromises();

    const buttons = wrapper.findAll("button");
    await buttons[buttons.length - 1]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-32");
  });
});
