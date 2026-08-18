import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import S63View from "./S-63.vue";
import type { ReflectionResult } from "../api/reflections";
import { useReflectionResultStore } from "../stores/reflectionResult";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));

function result(): ReflectionResult {
  return {
    looking_back: "Careerは前に進み、Financialは今週は手がつかなかったようです。",
    insight: "動けた目標には、その日のうちに終わる大きさがありました。",
    next_step: "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。",
    safety_flag: false,
    generated_at: "2026-08-07T09:01:00Z",
    answered_at: "2026-08-07T09:00:00Z",
  };
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
});

describe("S-63", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("結果を持たずに開かれたらS-61へ差し戻す", () => {
    mount(S63View);

    expect(replace).toHaveBeenCalledWith("/s-61");
  });

  it("振り返り・気づき・次の一歩の3要素と回答日付を表示する", () => {
    useReflectionResultStore().setResult(result());

    const wrapper = mount(S63View);

    expect(wrapper.text()).toContain("Careerは前に進み");
    expect(wrapper.text()).toContain("動けた目標には");
    expect(wrapper.text()).toContain("来週は、1日1回アプリを開くだけにしてみるのはどうでしょう");
    expect(wrapper.text()).toContain("2026年8月7日");
    expect(wrapper.find(".s63__card--primary").text()).toContain("次の一歩");
  });

  it("「ホームへ」でS-41へ遷移する", async () => {
    useReflectionResultStore().setResult(result());

    const wrapper = mount(S63View);
    await wrapper.find("button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-41");
  });

  it("safety_flagが立っていたら評価(振り返り・気づき・次の一歩)を表示しない", () => {
    useReflectionResultStore().setResult({ ...result(), safety_flag: true });

    const wrapper = mount(S63View);

    expect(wrapper.find(".s63__card").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Careerは前に進み");
    expect(wrapper.find('[data-testid="safety-notice"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("よりそいホットライン");
  });

  it("safety_flagが立っていても「ホームへ」は表示する(戻り先を残す)", async () => {
    useReflectionResultStore().setResult({ ...result(), safety_flag: true });

    const wrapper = mount(S63View);
    await wrapper.find("button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-41");
  });
});
