import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppHeaderHub from "./AppHeaderHub.vue";

describe("AppHeaderHub", () => {
  it("titleを省略するとロゴロックアップ(ブランド表示)を出し、戻る導線を持たない", () => {
    const wrapper = mount(AppHeaderHub);
    expect(wrapper.text()).toContain("Flourish Studio");
    expect(wrapper.find("svg").exists()).toBe(true);
    expect(wrapper.find("button").exists()).toBe(false);
  });

  it("titleを指定すると画面固有の文字列のみを出す(ロゴは出さない)", () => {
    const wrapper = mount(AppHeaderHub, { props: { title: "Flourish Map" } });
    expect(wrapper.text()).toBe("Flourish Map");
    expect(wrapper.find("svg").exists()).toBe(false);
  });

  it("right スロットに差し込める（テーマ切替トグルの受け皿）", () => {
    const wrapper = mount(AppHeaderHub, {
      slots: { right: "<button>テーマ</button>" },
    });
    expect(wrapper.find("button").text()).toBe("テーマ");
  });
});
