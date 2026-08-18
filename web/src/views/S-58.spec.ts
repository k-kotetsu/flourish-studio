import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S58View from "./S-58.vue";
import { getAreaPlan, updateAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/areaPlans", () => ({
  getAreaPlan: vi.fn(),
  updateAreaPlan: vi.fn(),
}));

const AREA_PLAN = {
  version: 1,
  area: "CAREER" as const,
  ideal_state:
    "今の仕事の中で自分の強みが言葉になっていて、次に何を任されたいかを自分から言えている。",
  selected_direction: "DEEPEN" as const,
  selected_label: "今の場所で深める",
  goals: [
    { goal_key: "g-1", body: "職務経歴書を書き上げる", sort_order: 1 },
    { goal_key: "g-2", body: "月に1回、社外の人と話す", sort_order: 2 },
  ],
  created_at: "2026-08-07T05:00:00Z",
};

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(getAreaPlan).mockReset();
  vi.mocked(updateAreaPlan).mockReset();
});

describe("S-58", () => {
  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S58View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("取得した理想の状態と目標を編集欄の初期値にする", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S58View);
    await flushPromises();

    expect(wrapper.find("#s58-ideal-state").element).toHaveProperty(
      "value",
      AREA_PLAN.ideal_state,
    );
    const inputs = wrapper.findAll(".s58__input");
    expect(inputs).toHaveLength(2);
    expect(inputs[0]!.element).toHaveProperty("value", "職務経歴書を書き上げる");
    expect(inputs[1]!.element).toHaveProperty("value", "月に1回、社外の人と話す");
  });

  it("取得に失敗したらエラーを表示し、編集欄は出さない", async () => {
    vi.mocked(getAreaPlan).mockRejectedValue(
      new ApiError(404, "AREA_PLAN_NOT_FOUND", "area plan has not been created yet"),
    );

    const wrapper = mount(S58View);
    await flushPromises();

    expect(wrapper.find(".s58__error--standalone").exists()).toBe(true);
    expect(wrapper.find("#s58-ideal-state").exists()).toBe(false);
  });

  it("「削除」で目標欄を1つ減らせる", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.findAll(".s58__remove")[1]!.trigger("click");

    const inputs = wrapper.findAll(".s58__input");
    expect(inputs).toHaveLength(1);
    expect(inputs[0]!.element).toHaveProperty("value", "職務経歴書を書き上げる");
  });

  it("「＋ 目標を追加」で3つ目の欄が増え、3つに達すると消える", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.find(".s58__ghost-button").trigger("click");

    expect(wrapper.findAll(".s58__input")).toHaveLength(3);
    expect(wrapper.findAll("button").filter((b) => b.text() === "＋ 目標を追加")).toHaveLength(0);
  });

  it("残り目標が0件になると「保存する」が無効になる", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue({
      ...AREA_PLAN,
      goals: [{ goal_key: "g-1", body: "職務経歴書を書き上げる", sort_order: 1 }],
    });

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.find(".s58__remove").trigger("click");

    expect(wrapper.find(".s58__cta button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("理想の状態と目標を1つ書くと、保存できます");
  });

  it("保存すると既存の目標はgoal_keyを引き継ぎ、新規の目標はキーなしで送る", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    vi.mocked(updateAreaPlan).mockResolvedValue({
      ...AREA_PLAN,
      version: 2,
      ideal_state: "書き換えた理想の状態。",
    });

    const wrapper = mount(S58View);
    await flushPromises();

    await wrapper.find("#s58-ideal-state").setValue("書き換えた理想の状態。");
    await wrapper.findAll(".s58__input")[0]!.setValue("職務経歴書を書き上げ、送った");
    await wrapper.find(".s58__ghost-button").trigger("click");
    await wrapper.findAll(".s58__input")[2]!.setValue("新しい目標");
    await wrapper.find(".s58__cta button").trigger("click");
    await flushPromises();

    expect(updateAreaPlan).toHaveBeenCalledWith("CAREER", {
      ideal_state: "書き換えた理想の状態。",
      goals: [
        { goal_key: "g-1", body: "職務経歴書を書き上げ、送った", sort_order: 1 },
        { goal_key: "g-2", body: "月に1回、社外の人と話す", sort_order: 2 },
        { body: "新しい目標", sort_order: 3 },
      ],
    });
    expect(push).toHaveBeenCalledWith("/s-57/career");
  });

  it("削除した目標のgoal_keyは送らない", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    vi.mocked(updateAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.findAll(".s58__remove")[1]!.trigger("click");
    await wrapper.find(".s58__cta button").trigger("click");
    await flushPromises();

    expect(updateAreaPlan).toHaveBeenCalledWith("CAREER", {
      ideal_state: AREA_PLAN.ideal_state,
      goals: [{ goal_key: "g-1", body: "職務経歴書を書き上げる", sort_order: 1 }],
    });
  });

  it("保存に失敗したらエラーを表示し、入力は消えない", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    vi.mocked(updateAreaPlan).mockRejectedValue(
      new ApiError(401, "UNAUTHENTICATED", "no session"),
    );

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.find("#s58-ideal-state").setValue("書き換えた理想の状態。");
    await wrapper.find(".s58__cta button").trigger("click");
    await flushPromises();

    expect(wrapper.find(".s58__body .s58__error").exists()).toBe(true);
    expect(wrapper.find("#s58-ideal-state").element).toHaveProperty(
      "value",
      "書き換えた理想の状態。",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("‹戻るで同じ領域のS-57へ戻す", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S58View);
    await flushPromises();
    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-57/career");
  });
});
