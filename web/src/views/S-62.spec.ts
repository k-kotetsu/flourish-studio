import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S62View from "./S-62.vue";
import { generateReflection } from "../api/reflections";
import { useReflectionAnswersStore } from "../stores/reflectionAnswers";
import { useReflectionResultStore } from "../stores/reflectionResult";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/reflections", () => ({
  generateReflection: vi.fn(),
}));

const resultBody = {
  looking_back: "前に進みました。",
  insight: "小さく区切れると動けるようです。",
  next_step: "来週は1日1回だけ開いてみるのはどうでしょう。",
  safety_flag: false,
  generated_at: "2026-08-08T09:01:00Z",
  answered_at: "2026-08-08T09:00:00Z",
};

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(generateReflection).mockReset();
});

describe("S-62", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("回答が無ければS-61へ差し戻す", async () => {
    mount(S62View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-61");
    expect(generateReflection).not.toHaveBeenCalled();
  });

  it("画面到達時に生成を呼び、成功したら結果を保存してS-63へ遷移する", async () => {
    const answersStore = useReflectionAnswersStore();
    answersStore.setAnswers({
      statuses: [{ goal_key: "g-1", status: "ON_TRACK" }],
      note: "今週は時間が取れなかった",
    });
    vi.mocked(generateReflection).mockResolvedValue(resultBody);

    mount(S62View);
    await flushPromises();

    expect(generateReflection).toHaveBeenCalledWith(
      [{ goal_key: "g-1", status: "ON_TRACK" }],
      "今週は時間が取れなかった",
      expect.any(AbortSignal),
    );
    expect(push).toHaveBeenCalledWith("/s-63");
    const resultStore = useReflectionResultStore();
    expect(resultStore.result).toEqual(resultBody);
  });

  it("失敗したら同じ画面の中身がエラー表示に入れ替わる(別画面へ遷移しない)", async () => {
    const answersStore = useReflectionAnswersStore();
    answersStore.setAnswers({ statuses: [{ goal_key: "g-1", status: "ON_TRACK" }], note: null });
    vi.mocked(generateReflection).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S62View);
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("うまくまとめられませんでした");
    expect(wrapper.text()).toContain("回答は、ちゃんと残っています");
  });

  it("「もう一度生成する」を押したときだけ再試行する(自動リトライしない)", async () => {
    const answersStore = useReflectionAnswersStore();
    answersStore.setAnswers({ statuses: [{ goal_key: "g-1", status: "ON_TRACK" }], note: null });
    vi.mocked(generateReflection).mockRejectedValueOnce(new Error("provider error"));
    vi.mocked(generateReflection).mockResolvedValueOnce(resultBody);

    const wrapper = mount(S62View);
    await flushPromises();
    expect(generateReflection).toHaveBeenCalledOnce();

    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(generateReflection).toHaveBeenCalledTimes(2);
    expect(push).toHaveBeenCalledWith("/s-63");
  });

  it("「回答に戻る」でS-61へ戻す", async () => {
    const answersStore = useReflectionAnswersStore();
    answersStore.setAnswers({ statuses: [{ goal_key: "g-1", status: "ON_TRACK" }], note: null });
    vi.mocked(generateReflection).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S62View);
    await flushPromises();

    const buttons = wrapper.findAll("button");
    await buttons[buttons.length - 1]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-61");
  });
});
