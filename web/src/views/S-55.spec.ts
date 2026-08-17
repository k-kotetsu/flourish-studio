import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S55View from "./S-55.vue";
import { getCurrentPurpose } from "../api/purposes";
import { ApiError } from "../api/client";
import { useAreaProposalsStore } from "../stores/areaProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/purposes", () => ({
  getCurrentPurpose: vi.fn(),
}));

const PURPOSE = {
  version: 1,
  statement: "自分で選んだと言えることを積み重ねて生きていきたい。",
  selected_direction: "SELF" as const,
  selected_label: "自分の納得を軸に",
  created_at: "2026-08-07T05:00:00Z",
};

const PROPOSALS = [
  { direction: "DEEPEN" as const, label: "今の場所で深める", ideal_state: "今の仕事の中で強みが言葉になっている。" },
  { direction: "CHANGE" as const, label: "やり方を変える", ideal_state: "働き方を一度組み替えている。" },
  { direction: "EXPAND" as const, label: "外に出る", ideal_state: "社外の人と接点を持てている。" },
];

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(getCurrentPurpose).mockReset();
});

describe("S-55", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S55View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("選ばれた案が無ければ同じ領域のS-54へ差し戻す", async () => {
    mount(S55View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-54/career");
  });

  it("ありたい姿と選んだ案の理想状態を表示する", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S55View);
    await flushPromises();

    expect(wrapper.text()).toContain(PURPOSE.statement);
    expect(wrapper.find("#s55-ideal-state").element).toHaveProperty("value", PROPOSALS[0]?.ideal_state);
  });

  it("ありたい姿の取得に失敗したらエラーを表示し、編集欄は表示しない", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockRejectedValue(new ApiError(401, "UNAUTHENTICATED", "no session"));

    const wrapper = mount(S55View);
    await flushPromises();

    expect(wrapper.find(".s55__error").exists()).toBe(true);
    expect(wrapper.find("#s55-ideal-state").exists()).toBe(false);
  });

  it("編集して「次へ」を押すとstoreに保存され、同じ領域のS-56へ進む", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S55View);
    await flushPromises();

    await wrapper.find("#s55-ideal-state").setValue("書き換えた理想の状態。");
    await wrapper.find(".s55__cta button").trigger("click");

    expect(store.editedIdealState).toBe("書き換えた理想の状態。");
    expect(push).toHaveBeenCalledWith("/s-56/career");
  });

  it("編集欄が空のあいだ「次へ」は無効で、補足が表示される", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S55View);
    await flushPromises();

    await wrapper.find("#s55-ideal-state").setValue("   ");

    expect(wrapper.find("button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("理想の状態を書くと、次に進めます");
  });

  it("「案を選び直す」で同じ領域のS-54へ遷移する", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S55View);
    await flushPromises();
    await wrapper.find(".s55__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-54/career");
  });

  it("‹戻るで同じ領域のS-54へ戻す", async () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S55View);
    await flushPromises();
    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-54/career");
  });
});
