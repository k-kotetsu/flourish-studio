import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AreaIcon from "./AreaIcon.vue";
import { AREAS } from "../domain/questions";

describe("AreaIcon", () => {
  it("4領域すべてを線画SVGで描画し、装飾として扱う(aria-hidden)", () => {
    for (const area of AREAS) {
      const wrapper = mount(AreaIcon, { props: { area } });
      const svg = wrapper.find("svg");
      expect(svg.attributes("aria-hidden")).toBe("true");
      expect(svg.attributes("fill")).toBe("none");
      expect(svg.attributes("stroke")).toBe("currentColor");
      expect(svg.attributes("stroke-width")).toBe("1.6");
    }
  });

  it("既定サイズは20pxで、sizeで変更できる", () => {
    const wrapper = mount(AreaIcon, { props: { area: "CAREER" } });
    expect(wrapper.find("svg").attributes("width")).toBe("20");

    const resized = mount(AreaIcon, { props: { area: "CAREER", size: 28 } });
    expect(resized.find("svg").attributes("width")).toBe("28");
  });
});
