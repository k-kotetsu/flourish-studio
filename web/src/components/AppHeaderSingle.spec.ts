import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppHeaderSingle from "./AppHeaderSingle.vue";

describe("AppHeaderSingle", () => {
  it("画面名を表示し、プログレスバーを持たない", () => {
    const wrapper = mount(AppHeaderSingle, { props: { title: "Career" } });
    expect(wrapper.text()).toContain("Career");
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false);
  });

  it("戻るを押すと back を発火する", async () => {
    const wrapper = mount(AppHeaderSingle, { props: { title: "Career" } });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("back")).toHaveLength(1);
  });
});
