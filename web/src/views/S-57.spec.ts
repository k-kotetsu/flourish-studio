import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S57View from "./S-57.vue";
import { getAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/areaPlans", () => ({
  getAreaPlan: vi.fn(),
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
});

describe("S-57", () => {
  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S57View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("取得した理想の状態と目標一覧を表示する", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);

    const wrapper = mount(S57View);
    await flushPromises();

    expect(getAreaPlan).toHaveBeenCalledWith("CAREER");
    expect(wrapper.text()).toContain(AREA_PLAN.ideal_state);
    expect(wrapper.text()).toContain("職務経歴書を書き上げる");
    expect(wrapper.text()).toContain("月に1回、社外の人と話す");
  });

  it("取得に失敗したらエラーを表示する", async () => {
    vi.mocked(getAreaPlan).mockRejectedValue(
      new ApiError(404, "AREA_PLAN_NOT_FOUND", "area plan has not been created yet"),
    );

    const wrapper = mount(S57View);
    await flushPromises();

    expect(wrapper.text()).toContain("うまくいきませんでした");
  });

  it("「編集する」で同じ領域のS-58へ遷移する", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    const wrapper = mount(S57View);
    await flushPromises();

    await wrapper.find("button.app-button--secondary").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-58/career");
  });

  it("「AIと話して見直す」で同じ領域のS-51へ遷移する", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    const wrapper = mount(S57View);
    await flushPromises();

    await wrapper.find(".s57__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-51/career");
  });

  it("‹戻るでS-41へ遷移する", async () => {
    vi.mocked(getAreaPlan).mockResolvedValue(AREA_PLAN);
    const wrapper = mount(S57View);
    await flushPromises();

    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-41");
  });
});
