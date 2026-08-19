import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S61View from "./S-61.vue";
import { getReflectionContext, type ReflectionContextResponse } from "../api/reflections";
import { ApiError } from "../api/client";
import { useReflectionAnswersStore } from "../stores/reflectionAnswers";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/reflections", () => ({
  getReflectionContext: vi.fn(),
}));

const CONTEXT: ReflectionContextResponse = {
  goals: [
    { goal_key: "g-career-1", area: "CAREER", body: "職務経歴書を書き上げる" },
    { goal_key: "g-social-1", area: "SOCIAL", body: "家族と週末に話す時間を取る" },
  ],
};

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(getReflectionContext).mockReset();
});

describe("S-61", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("目標一覧と領域名、自由記述欄を表示する", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    await flushPromises();

    expect(wrapper.text()).toContain("職務経歴書を書き上げる");
    expect(wrapper.text()).toContain("家族と週末に話す時間を取る");
    expect(wrapper.text()).toContain("Career");
    expect(wrapper.text()).toContain("Social");
    expect(wrapper.find("textarea").exists()).toBe(true);
    expect(wrapper.findAll(".s61__area-heading svg")).toHaveLength(2); // P7-3: 4領域アイコン
  });

  it("取得に失敗したらエラーを表示する", async () => {
    vi.mocked(getReflectionContext).mockRejectedValue(new ApiError(401, "UNAUTHENTICATED", "no session"));
    const wrapper = mount(S61View);
    await flushPromises();

    expect(wrapper.find(".s61__error").exists()).toBe(true);
  });

  it("目標が0件ならS-41へ戻す(screen-list.mdの前提「目標が1個以上あること」)", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue({ goals: [] });
    mount(S61View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-41");
  });

  it("すべての目標に回答するまで「送信する」は無効で、補足が表示される", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    await flushPromises();

    expect(wrapper.find("button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("すべて選ぶと、送信できます");
  });

  it("すべての目標に回答して送信すると、storeに記録しS-62へ遷移する", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    const store = useReflectionAnswersStore();
    await flushPromises();

    const rows = wrapper.findAll(".s61__row");
    await rows[0]!.findAll(".s61__status-input")[0]!.setValue(); // 進んでいる
    await rows[1]!.findAll(".s61__status-input")[1]!.setValue(); // 止まっている
    await wrapper.find("textarea").setValue("今週は残業が続いた");
    await wrapper.find(".s61__cta button").trigger("click");

    expect(store.statuses).toEqual([
      { goal_key: "g-career-1", status: "ON_TRACK" },
      { goal_key: "g-social-1", status: "STALLED" },
    ]);
    expect(store.note).toBe("今週は残業が続いた");
    expect(push).toHaveBeenCalledWith("/s-62");
  });

  it("自由記述が空欄なら note は null で送る(任意入力)", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    const store = useReflectionAnswersStore();
    await flushPromises();

    const rows = wrapper.findAll(".s61__row");
    await rows[0]!.findAll(".s61__status-input")[0]!.setValue();
    await rows[1]!.findAll(".s61__status-input")[0]!.setValue();
    await wrapper.find(".s61__cta button").trigger("click");

    expect(store.note).toBeNull();
  });

  it("「× 中断」→「やめる」でS-41へ遷移する", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    await flushPromises();
    await wrapper.find(".app-header-single__nav").trigger("click");
    const leaveButton = document.body.querySelectorAll(".interrupt-dialog button")[1] as HTMLButtonElement;
    leaveButton.click();
    await flushPromises();

    expect(push).toHaveBeenCalledWith("/s-41");
    wrapper.unmount();
  });

  it("「× 中断」→「つづける」では遷移せず、ダイアログが閉じる", async () => {
    vi.mocked(getReflectionContext).mockResolvedValue(CONTEXT);
    const wrapper = mount(S61View);
    await flushPromises();
    await wrapper.find(".app-header-single__nav").trigger("click");
    expect(document.body.querySelector(".interrupt-dialog")).not.toBeNull();

    const continueButton = document.body.querySelectorAll(".interrupt-dialog button")[0] as HTMLButtonElement;
    continueButton.click();
    await flushPromises();

    expect(document.body.querySelector(".interrupt-dialog")).toBeNull();
    expect(push).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
