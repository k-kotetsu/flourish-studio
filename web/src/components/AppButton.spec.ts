import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppButton from "./AppButton.vue";

describe("AppButton", () => {
  it("既定は主要ボタンとして描画される", () => {
    const wrapper = mount(AppButton, { slots: { default: "次へ" } });
    expect(wrapper.classes()).toContain("app-button--primary");
    expect(wrapper.text()).toBe("次へ");
  });

  it.each(["primary", "secondary", "text"] as const)(
    "variant=%s のクラスが付く",
    (variant) => {
      const wrapper = mount(AppButton, { props: { variant } });
      expect(wrapper.classes()).toContain(`app-button--${variant}`);
    },
  );

  it("クリックで click イベントを発火する", async () => {
    const wrapper = mount(AppButton);
    await wrapper.trigger("click");
    expect(wrapper.emitted("click")).toHaveLength(1);
  });

  it("無効時は disabled 属性が付く（無効ボタンは消さずに残す）", () => {
    const wrapper = mount(AppButton, { props: { disabled: true } });
    expect(wrapper.attributes("disabled")).toBeDefined();
    expect(wrapper.classes()).toContain("app-button--primary");
  });
});
