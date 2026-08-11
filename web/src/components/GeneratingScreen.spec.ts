import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GeneratingScreen from "./GeneratingScreen.vue";

describe("GeneratingScreen", () => {
  it("待ち状態では具体的な進行メッセージを表示する", () => {
    const wrapper = mount(GeneratingScreen, {
      props: { message: "あなたに合わせた質問を用意しています" },
    });
    expect(wrapper.text()).toContain("あなたに合わせた質問を用意しています");
    expect(wrapper.find("button").exists()).toBe(false);
  });

  it("失敗時は同じコンポーネントの中身がエラー表示に入れ替わる", () => {
    const wrapper = mount(GeneratingScreen, {
      props: {
        message: "生成しています",
        failed: true,
        errorMessage: "時間がかかりすぎました。もう一度お試しください。",
        retryLabel: "もう一度生成する",
      },
    });
    expect(wrapper.text()).not.toContain("生成しています");
    expect(wrapper.text()).toContain("時間がかかりすぎました");
    expect(wrapper.text()).toContain("もう一度生成する");
  });

  it("再試行ボタンで retry を発火する（自動リトライしない）", async () => {
    const wrapper = mount(GeneratingScreen, {
      props: { message: "生成しています", failed: true, errorMessage: "失敗しました" },
    });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
  });

  it("backLabel を渡したときだけ戻り導線を出す", () => {
    const withoutBack = mount(GeneratingScreen, {
      props: { message: "生成しています", failed: true, errorMessage: "失敗しました" },
    });
    expect(withoutBack.findAll("button")).toHaveLength(1);

    const withBack = mount(GeneratingScreen, {
      props: {
        message: "生成しています",
        failed: true,
        errorMessage: "失敗しました",
        backLabel: "対話に戻る",
      },
    });
    expect(withBack.text()).toContain("対話に戻る");
  });
});
