import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S54View from "./S-54.vue";
import { useAreaProposalsStore } from "../stores/areaProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));

// サーバー側で順序は検証済みだが、表示側もAI出力の順序に依存しないことを確認するため
// 意図的にDEEPEN/CHANGE/EXPAND以外の並びにする
const PROPOSALS_OUT_OF_ORDER = [
  { direction: "EXPAND" as const, label: "外に出る", ideal_state: "…持てている。" },
  { direction: "DEEPEN" as const, label: "今の場所で深める", ideal_state: "…できている。" },
  { direction: "CHANGE" as const, label: "やり方を変える", ideal_state: "…見つかっている。" },
];

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
});

describe("S-54", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S54View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("3案揃っていなければ同じ領域のS-51へ差し戻す", async () => {
    mount(S54View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-51/career");
  });

  it("3案をDEEPEN→CHANGE→EXPANDの順に表示する(AI出力の順序に依存しない)", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S54View);

    const labels = wrapper.findAll(".s54__proposal-label").map((node) => node.text());
    expect(labels).toEqual(["今の場所で深める", "やり方を変える", "外に出る"]);
  });

  it("どれも選ばれていない間は「この案で進む」が無効", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S54View);

    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("1つ選ぶと、次に進めます");
  });

  it("1案を選ぶと「この案で進む」が有効になり、同じ領域のS-55へ進める", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S54View);
    // 表示は固定順(DEEPEN→CHANGE→EXPAND)のため、最初のラジオはDEEPEN
    await wrapper.find("input[type='radio']").trigger("change");

    expect(store.selectedDirection).toBe("DEEPEN");
    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeUndefined();

    await submit.trigger("click");
    expect(push).toHaveBeenCalledWith("/s-55/career");
  });

  it("「3つとも作り直す」で同じ領域のS-53へ遷移する", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S54View);
    await wrapper.find(".s54__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-53/career");
  });

  it("‹戻るで同じ領域のS-52へ戻す", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS_OUT_OF_ORDER);

    const wrapper = mount(S54View);
    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-52/career");
  });
});
