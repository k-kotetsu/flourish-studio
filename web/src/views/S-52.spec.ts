import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S52View from "./S-52.vue";
import { AreaDialogueError, streamAreaDialogue } from "../api/areaDialogue";
import { ApiError } from "../api/client";
import { getCurrentPurpose } from "../api/purposes";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/purposes", () => ({
  getCurrentPurpose: vi.fn(),
}));
vi.mock("../api/areaDialogue", async () => {
  const actual = await vi.importActual<typeof import("../api/areaDialogue")>(
    "../api/areaDialogue",
  );
  return { ...actual, streamAreaDialogue: vi.fn() };
});

const PURPOSE = {
  version: 1,
  statement: "まわりの人が安心して力を出せる存在でありたい。",
  selected_direction: "OTHERS" as const,
  selected_label: "まわりの人とともに",
  created_at: "2026-08-07T05:00:00Z",
};

function setValidChoices(): void {
  const store = useAreaChoicesStore();
  store.setAnswers({
    area: "CAREER",
    changeItemCode: "CAREER_OUTLOOK",
    values: ["CAREER_VALUE_GROWTH"],
    positions: ["CAREER_POSITION_GROWTH"],
  });
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(getCurrentPurpose).mockReset();
  vi.mocked(streamAreaDialogue).mockReset();
});

describe("S-52", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S52View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
    expect(streamAreaDialogue).not.toHaveBeenCalled();
  });

  it("S-51の選択が揃っていなければ同じ領域のS-51へ差し戻す", async () => {
    mount(S52View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-51/career");
    expect(streamAreaDialogue).not.toHaveBeenCalled();
  });

  it("ありたい姿を常時表示する", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(streamAreaDialogue).mockResolvedValue({
      turn: 1,
      remaining: 1,
      safety_flag: false,
    });

    const wrapper = mount(S52View);
    await flushPromises();

    expect(wrapper.text()).toContain(PURPOSE.statement);
  });

  it("画面到達時(履歴が空)にAI主導の1往復目を自動生成し、逐次表示される", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    let calledWithArea: unknown;
    vi.mocked(streamAreaDialogue).mockImplementation(async (area, _choices, messages, callbacks) => {
      calledWithArea = area;
      expect(messages).toEqual([]);
      callbacks.onDelta("キャリアの見通しを");
      callbacks.onDelta("選ばれていました。");
      return { turn: 1, remaining: 1, safety_flag: false };
    });

    const wrapper = mount(S52View);
    await flushPromises();

    expect(streamAreaDialogue).toHaveBeenCalledOnce();
    expect(calledWithArea).toBe("CAREER");
    expect(wrapper.text()).toContain("キャリアの見通しを選ばれていました。");

    const dialogueStore = useAreaDialogueStore();
    expect(dialogueStore.messages).toEqual([
      { role: "AI", body: "キャリアの見通しを選ばれていました。" },
    ]);
    expect(dialogueStore.remaining).toBe(1);
  });

  it("履歴が既にある場合は1往復目を自動生成しない", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const dialogueStore = useAreaDialogueStore();
    dialogueStore.addMessage({ role: "AI", body: "既存の発言" });

    mount(S52View);
    await flushPromises();

    expect(streamAreaDialogue).not.toHaveBeenCalled();
  });

  it("remainingが0になると「理想の状態を作る」が現れ、押すとS-53(同じ領域)へ遷移する", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(streamAreaDialogue).mockResolvedValueOnce({
      turn: 2,
      remaining: 0,
      safety_flag: false,
    });

    const wrapper = mount(S52View);
    await flushPromises();

    const button = wrapper.findAll("button").find((b) => b.text() === "理想の状態を作る");
    expect(button).toBeDefined();
    await button?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-53/career");
  });

  it("失敗時は直近の発言位置にエラーと再送ボタンを出し、ユーザーの発言は残す", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(streamAreaDialogue).mockRejectedValueOnce(
      new AreaDialogueError("AI_PROVIDER_ERROR"),
    );

    const wrapper = mount(S52View);
    await flushPromises();

    expect(wrapper.text()).toContain("うまく届きませんでした");
    expect(wrapper.text()).toContain("書いていただいた内容はそのまま残っています");
    expect(push).not.toHaveBeenCalled();
  });

  it("「‹ 戻る」でS-51(同じ領域)へ直接遷移する", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(streamAreaDialogue).mockResolvedValue({
      turn: 1,
      remaining: 1,
      safety_flag: false,
    });

    const wrapper = mount(S52View);
    await flushPromises();

    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-51/career");
  });

  it("ありたい姿の取得に失敗した場合はエラーを表示し、チャットを出さない", async () => {
    setValidChoices();
    vi.mocked(getCurrentPurpose).mockRejectedValue(
      new ApiError(401, "UNAUTHENTICATED", "no session"),
    );

    const wrapper = mount(S52View);
    await flushPromises();

    expect(wrapper.find(".s52__error-standalone").exists()).toBe(true);
    expect(wrapper.find(".s52__composer").exists()).toBe(false);
  });
});
