import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S32View from "./S-32.vue";
import { PurposeDialogueError, streamPurposeDialogue } from "../api/purposeDialogue";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/purposeDialogue", async () => {
  const actual = await vi.importActual<typeof import("../api/purposeDialogue")>(
    "../api/purposeDialogue",
  );
  return { ...actual, streamPurposeDialogue: vi.fn() };
});

function setValidChoices(): void {
  const store = usePurposeChoicesStore();
  store.setAnswers({
    values: ["GROWTH"],
    fulfillingMoments: ["HELPED_SOMEONE"],
    idealDailyLife: "HAVING_OPTIONS",
  });
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(streamPurposeDialogue).mockReset();
});

describe("S-32", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("S-31の選択が揃っていなければS-31へ差し戻す", async () => {
    mount(S32View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-31");
    expect(streamPurposeDialogue).not.toHaveBeenCalled();
  });

  it("画面到達時(履歴が空)にAI主導の1往復目を自動生成し、逐次表示される", async () => {
    setValidChoices();
    let messagesAtCallTime: unknown;
    vi.mocked(streamPurposeDialogue).mockImplementation(async (_choices, messages, callbacks) => {
      messagesAtCallTime = [...messages];
      callbacks.onDelta("「成長」を");
      callbacks.onDelta("選ばれていました。");
      return { turn: 1, remaining: 2, safety_flag: false };
    });

    const wrapper = mount(S32View);
    await flushPromises();

    expect(streamPurposeDialogue).toHaveBeenCalledOnce();
    expect(messagesAtCallTime).toEqual([]);
    expect(wrapper.text()).toContain("「成長」を選ばれていました。");

    const dialogueStore = usePurposeDialogueStore();
    expect(dialogueStore.messages).toEqual([
      { role: "AI", body: "「成長」を選ばれていました。" },
    ]);
    expect(dialogueStore.remaining).toBe(2);
  });

  it("履歴が既にある場合は1往復目を自動生成しない", async () => {
    setValidChoices();
    const dialogueStore = usePurposeDialogueStore();
    dialogueStore.addMessage({ role: "AI", body: "既存の発言" });

    mount(S32View);
    await flushPromises();

    expect(streamPurposeDialogue).not.toHaveBeenCalled();
  });

  it("メッセージを送信すると履歴に積み、AI応答を待つ", async () => {
    setValidChoices();
    vi.mocked(streamPurposeDialogue).mockResolvedValueOnce({
      turn: 1,
      remaining: 2,
      safety_flag: false,
    }); // 1往復目(自動)
    vi.mocked(streamPurposeDialogue).mockImplementationOnce(async (_c, _m, callbacks) => {
      callbacks.onDelta("次の問いです。");
      return { turn: 2, remaining: 1, safety_flag: false };
    });

    const wrapper = mount(S32View);
    await flushPromises();

    await wrapper.find("input").setValue("前の職場で感じたこと");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    const dialogueStore = usePurposeDialogueStore();
    expect(dialogueStore.messages).toContainEqual({
      role: "USER",
      body: "前の職場で感じたこと",
    });
    expect(dialogueStore.messages).toContainEqual({ role: "AI", body: "次の問いです。" });
    expect(dialogueStore.remaining).toBe(1);
  });

  it("remainingが0になると「候補を作る」が現れ、押すとS-33へ遷移する", async () => {
    setValidChoices();
    vi.mocked(streamPurposeDialogue).mockResolvedValueOnce({
      turn: 3,
      remaining: 0,
      safety_flag: false,
    });

    const wrapper = mount(S32View);
    await flushPromises();

    const button = wrapper.findAll("button").find((b) => b.text() === "候補を作る");
    expect(button).toBeDefined();
    await button?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-33");
  });

  it("失敗時は直近の発言位置にエラーと再送ボタンを出し、ユーザーの発言は残す", async () => {
    setValidChoices();
    vi.mocked(streamPurposeDialogue).mockRejectedValueOnce(
      new PurposeDialogueError("AI_PROVIDER_ERROR"),
    );

    const wrapper = mount(S32View);
    await flushPromises();

    expect(wrapper.text()).toContain("うまく届きませんでした");
    expect(wrapper.text()).toContain("書いていただいた内容はそのまま残っています");
    expect(push).not.toHaveBeenCalled();
  });

  it("「もう一度送る」を押したときだけ再試行する(自動リトライしない)", async () => {
    setValidChoices();
    vi.mocked(streamPurposeDialogue).mockRejectedValueOnce(
      new PurposeDialogueError("AI_PROVIDER_ERROR"),
    );
    vi.mocked(streamPurposeDialogue).mockImplementationOnce(async (_c, _m, callbacks) => {
      callbacks.onDelta("復帰しました。");
      return { turn: 1, remaining: 2, safety_flag: false };
    });

    const wrapper = mount(S32View);
    await flushPromises();
    expect(streamPurposeDialogue).toHaveBeenCalledOnce();

    const retryButton = wrapper.findAll("button").find((b) => b.text() === "もう一度送る");
    await retryButton?.trigger("click");
    await flushPromises();

    expect(streamPurposeDialogue).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("復帰しました。");
    expect(wrapper.text()).not.toContain("うまく届きませんでした");
  });

  it("応答待ちの間は入力欄と送信を無効にする", async () => {
    setValidChoices();
    let resolveStream: (value: { turn: number; remaining: number; safety_flag: boolean }) => void =
      () => {};
    vi.mocked(streamPurposeDialogue).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveStream = resolve;
      }),
    );

    const wrapper = mount(S32View);
    await flushPromises();

    expect((wrapper.find("input").element as HTMLInputElement).disabled).toBe(true);

    resolveStream({ turn: 1, remaining: 2, safety_flag: false });
    await flushPromises();

    expect((wrapper.find("input").element as HTMLInputElement).disabled).toBe(false);
  });
});
