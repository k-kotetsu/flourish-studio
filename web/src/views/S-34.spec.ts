import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S34View from "./S-34.vue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));

// AI出力の順序に依存しないことを確認するため、意図的にSELF/OTHERS/SOCIETY以外の並びにする
const PROPOSALS_OUT_OF_ORDER = [
  { direction: "SOCIETY" as const, label: "もっと広く", statement: "人の可能性が広がる場をつくっていきたい。" },
  { direction: "SELF" as const, label: "自分の納得を軸に", statement: "自分で選んだと言えることを積み重ねて生きていきたい。" },
  { direction: "OTHERS" as const, label: "まわりの人とともに", statement: "まわりの人が安心して力を出せる存在でありたい。" },
];

afterEach(() => {
  push.mockReset();
  replace.mockReset();
});

describe("S-34", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("3案揃っていなければS-31へ差し戻す", async () => {
    mount(S34View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-31");
  });

  it("3案をSELF→OTHERS→SOCIETYの順に表示する(AI出力の順序に依存しない)", () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S34View);

    const labels = wrapper.findAll(".s34__proposal-label").map((node) => node.text());
    expect(labels).toEqual(["自分の納得を軸に", "まわりの人とともに", "もっと広く"]);
  });

  it("どれも選ばれていない間は「この案で進む」が無効", () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S34View);

    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("1つ選ぶと、次に進めます");
  });

  it("1案を選ぶと「この案で進む」が有効になり、次へ進める", async () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S34View);
    await wrapper.find("input[type='radio']").trigger("change");

    expect(store.selectedDirection).toBe("SELF");
    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeUndefined();

    await submit.trigger("click");
    expect(push).toHaveBeenCalledWith("/s-35");
  });

  it("「3つとも作り直す」でS-33へ遷移する", async () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S34View);
    await wrapper.find(".s34__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-33");
  });

  it("‹戻るでS-32へ戻す", async () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S34View);
    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-32");
  });
});
