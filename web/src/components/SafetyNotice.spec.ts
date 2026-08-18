import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import SafetyNotice from "./SafetyNotice.vue";

describe("SafetyNotice", () => {
  it("相談窓口の固定文面を表示する", () => {
    const wrapper = mount(SafetyNotice);
    expect(wrapper.find('[data-testid="safety-notice"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("よりそいホットライン");
    expect(wrapper.text()).toContain("0120-279-338");
    expect(wrapper.text()).toContain("いのちの電話");
    expect(wrapper.text()).toContain("まもろうよ こころ");
  });
});
