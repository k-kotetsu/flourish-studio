import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppHeaderHub from "./AppHeaderHub.vue";

describe("AppHeaderHub", () => {
  it("既定タイトルを表示し、戻る導線を持たない", () => {
    const wrapper = mount(AppHeaderHub);
    expect(wrapper.text()).toContain("Flourish Studio");
    expect(wrapper.find("button").exists()).toBe(false);
  });

  it("right スロットに差し込める（テーマ切替トグルの受け皿）", () => {
    const wrapper = mount(AppHeaderHub, {
      slots: { right: "<button>テーマ</button>" },
    });
    expect(wrapper.find("button").text()).toBe("テーマ");
  });
});
