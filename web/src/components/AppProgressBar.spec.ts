import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppProgressBar from "./AppProgressBar.vue";

describe("AppProgressBar", () => {
  it("percent を幅とaria-valuenowに反映する", () => {
    const wrapper = mount(AppProgressBar, { props: { percent: 67 } });
    expect(wrapper.attributes("aria-valuenow")).toBe("67");
    expect(wrapper.find(".app-progress-bar__fill").attributes("style")).toContain(
      "width: 67%",
    );
  });

  it("role=progressbar を持つ", () => {
    const wrapper = mount(AppProgressBar, { props: { percent: 0 } });
    expect(wrapper.attributes("role")).toBe("progressbar");
  });
});
