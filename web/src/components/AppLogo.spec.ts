import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppLogo from "./AppLogo.vue";

describe("AppLogo", () => {
  it("ロゴマーク(線画SVG)とサービス名を組みで表示する", () => {
    const wrapper = mount(AppLogo);

    const svg = wrapper.find("svg");
    expect(svg.attributes("aria-hidden")).toBe("true");
    expect(svg.attributes("stroke")).toBe("currentColor");
    expect(wrapper.text()).toBe("Flourish Studio");
  });

  it("既定サイズは22pxで、sizeで変更できる", () => {
    const wrapper = mount(AppLogo);
    expect(wrapper.find("svg").attributes("width")).toBe("22");

    const resized = mount(AppLogo, { props: { size: 32 } });
    expect(resized.find("svg").attributes("width")).toBe("32");
  });
});
