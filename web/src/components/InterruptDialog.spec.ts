import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import InterruptDialog from "./InterruptDialog.vue";

describe("InterruptDialog", () => {
  it("open=false では描画されない", () => {
    const wrapper = mount(InterruptDialog, { props: { open: false } });
    expect(document.body.querySelector(".interrupt-dialog")).toBeNull();
    wrapper.unmount();
  });

  it("open=true では固定文言のダイアログを表示する", () => {
    const wrapper = mount(InterruptDialog, { props: { open: true } });
    const dialog = document.body.querySelector(".interrupt-dialog");
    expect(dialog?.textContent).toContain("ここでやめますか？");
    expect(dialog?.textContent).toContain("いま中断すると");
    wrapper.unmount();
  });

  it("「つづける」が主ボタンで continue を発火する", async () => {
    const wrapper = mount(InterruptDialog, { props: { open: true } });
    const buttons = document.body.querySelectorAll(".interrupt-dialog button");
    expect(buttons[0].textContent?.trim()).toBe("つづける");
    expect(buttons[0].className).toContain("app-button--primary");
    (buttons[0] as HTMLButtonElement).click();
    expect(wrapper.emitted("continue")).toHaveLength(1);
    wrapper.unmount();
  });

  it("「やめる」を押すと leave を発火する", () => {
    const wrapper = mount(InterruptDialog, { props: { open: true } });
    const buttons = document.body.querySelectorAll(".interrupt-dialog button");
    expect(buttons[1].textContent?.trim()).toBe("やめる");
    (buttons[1] as HTMLButtonElement).click();
    expect(wrapper.emitted("leave")).toHaveLength(1);
    wrapper.unmount();
  });
});
