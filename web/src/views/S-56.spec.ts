import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S56View from "./S-56.vue";
import { createAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";
import { generateGoalHints } from "../api/goalHints";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";
import { useAreaProposalsStore } from "../stores/areaProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
const routeParams = vi.hoisted(() => ({ area: "career" }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => ({ params: routeParams }),
}));
vi.mock("../api/areaPlans", () => ({
  createAreaPlan: vi.fn(),
}));
vi.mock("../api/goalHints", () => ({
  generateGoalHints: vi.fn(),
}));

const PROPOSALS = [
  {
    direction: "DEEPEN" as const,
    label: "今の場所で深める",
    ideal_state: "今の仕事の中で強みが言葉になっている。",
  },
  {
    direction: "CHANGE" as const,
    label: "やり方を変える",
    ideal_state: "働き方を一度組み替えている。",
  },
  { direction: "EXPAND" as const, label: "外に出る", ideal_state: "社外の人と接点を持てている。" },
];

function setupReadyState(): void {
  const proposalsStore = useAreaProposalsStore();
  proposalsStore.setProposals(PROPOSALS);
  proposalsStore.select("DEEPEN");
  proposalsStore.setEditedIdealState("編集後の理想の状態。");

  const choicesStore = useAreaChoicesStore();
  choicesStore.setAnswers({
    area: "CAREER",
    changeItemCode: "CAREER_OUTLOOK",
    values: ["CAREER_VALUE_GROWTH"],
    positions: ["CAREER_POSITION_GROWTH"],
  });

  const dialogueStore = useAreaDialogueStore();
  dialogueStore.addMessage({ role: "AI", body: "問い" });
  dialogueStore.addMessage({ role: "USER", body: "答え" });
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  routeParams.area = "career";
  vi.mocked(createAreaPlan).mockReset();
  vi.mocked(generateGoalHints).mockReset();
});

describe("S-56", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("未知の領域パラメータではS-50へ戻す", async () => {
    routeParams.area = "unknown";
    mount(S56View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-50");
  });

  it("選ばれた案が無ければ同じ領域のS-54へ差し戻す", async () => {
    mount(S56View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-54/career");
  });

  it("編集後の理想状態が無ければ同じ領域のS-55へ差し戻す", async () => {
    const proposalsStore = useAreaProposalsStore();
    proposalsStore.setProposals(PROPOSALS);
    proposalsStore.select("DEEPEN");

    mount(S56View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-55/career");
  });

  it("理想の状態を上部に表示し、目標欄を2つ既定表示する", async () => {
    setupReadyState();

    const wrapper = mount(S56View);
    await flushPromises();

    expect(wrapper.text()).toContain("編集後の理想の状態。");
    expect(wrapper.findAll(".s56__input")).toHaveLength(2);
  });

  it("1つ目の目標が空のあいだ「確定する」は無効で、補足が表示される", async () => {
    setupReadyState();

    const wrapper = mount(S56View);
    await flushPromises();

    expect(wrapper.find(".s56__cta button[disabled]").exists()).toBe(true);
    expect(wrapper.text()).toContain("目標を1つ書くと、確定できます");
  });

  it("1つ目に入力すると「確定する」が有効になる", async () => {
    setupReadyState();

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.findAll(".s56__input")[0]!.setValue("職務経歴書を書き上げる");

    expect(wrapper.find(".s56__cta button[disabled]").exists()).toBe(false);
  });

  it("「＋ 目標を追加」で3つ目の欄が増え、3つに達すると消える", async () => {
    setupReadyState();

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.find(".s56__ghost-button").trigger("click");

    expect(wrapper.findAll(".s56__input")).toHaveLength(3);
    expect(wrapper.findAll("button").filter((b) => b.text() === "＋ 目標を追加")).toHaveLength(0);
  });

  it("AIにヒントをもらうと候補3件を表示し、押すと空欄に反映する", async () => {
    setupReadyState();
    vi.mocked(generateGoalHints).mockResolvedValue(["候補1", "候補2", "候補3"]);

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.find(".s56__hint-prompt .s56__ghost-button").trigger("click");
    await flushPromises();

    expect(generateGoalHints).toHaveBeenCalledWith(
      "CAREER",
      "編集後の理想の状態。",
      [],
      expect.any(AbortSignal),
    );
    const options = wrapper.findAll(".s56__hint-option");
    expect(options).toHaveLength(3);

    await options[0]!.trigger("click");
    expect(wrapper.findAll(".s56__input")[0]!.element).toHaveProperty("value", "候補1");
  });

  it("ヒント取得に失敗したらエラー文言を表示し、画面遷移しない", async () => {
    setupReadyState();
    vi.mocked(generateGoalHints).mockRejectedValue(
      new ApiError(503, "AI_PROVIDER_ERROR", "failed"),
    );

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.find(".s56__hint-prompt .s56__ghost-button").trigger("click");
    await flushPromises();

    expect(wrapper.find(".s56__error").exists()).toBe(true);
    expect(push).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalledWith("/s-41");
  });

  it("確定すると正しい引数でcreateAreaPlanを呼び、成功したらストアをリセットしてS-41へ進む", async () => {
    setupReadyState();
    vi.mocked(createAreaPlan).mockResolvedValue({
      version: 1,
      area: "CAREER",
      ideal_state: "編集後の理想の状態。",
      selected_direction: "DEEPEN",
      selected_label: "今の場所で深める",
      goals: [{ goal_key: "g-1", body: "職務経歴書を書き上げる", sort_order: 1 }],
      created_at: "2026-08-17T00:00:00Z",
    });

    const choicesStore = useAreaChoicesStore();
    const dialogueStore = useAreaDialogueStore();
    const proposalsStore = useAreaProposalsStore();
    const expectedChoices = choicesStore.asChoices;

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.findAll(".s56__input")[0]!.setValue("職務経歴書を書き上げる");
    await wrapper.find(".s56__cta button").trigger("click");
    await flushPromises();

    expect(createAreaPlan).toHaveBeenCalledWith({
      area: "CAREER",
      choices: expectedChoices,
      messages: [
        { role: "AI", body: "問い" },
        { role: "USER", body: "答え" },
      ],
      selected_direction: "DEEPEN",
      selected_label: "今の場所で深める",
      original_ideal_state: "今の仕事の中で強みが言葉になっている。",
      ideal_state: "編集後の理想の状態。",
      goals: [{ body: "職務経歴書を書き上げる", sort_order: 1 }],
    });
    expect(choicesStore.area).toBeNull();
    expect(dialogueStore.messages).toEqual([]);
    expect(proposalsStore.proposals).toEqual([]);
    expect(push).toHaveBeenCalledWith("/s-41");
  });

  it("確定に失敗したらエラー文言を表示し、入力は消えない", async () => {
    setupReadyState();
    vi.mocked(createAreaPlan).mockRejectedValue(
      new ApiError(409, "PURPOSE_REQUIRED", "purpose missing"),
    );

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.findAll(".s56__input")[0]!.setValue("職務経歴書を書き上げる");
    await wrapper.find(".s56__cta button").trigger("click");
    await flushPromises();

    expect(wrapper.find(".s56__cta .s56__error").exists()).toBe(true);
    expect(wrapper.findAll(".s56__input")[0]!.element).toHaveProperty(
      "value",
      "職務経歴書を書き上げる",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("‹戻るで同じ領域のS-55へ戻す", async () => {
    setupReadyState();

    const wrapper = mount(S56View);
    await flushPromises();
    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-55/career");
  });
});
