import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S35View from "./S-35.vue";
import { createPurpose } from "../api/purposes";
import { ApiError } from "../api/client";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/purposes", () => ({
  createPurpose: vi.fn(),
}));

const SELECTED_PROPOSAL = {
  direction: "SELF" as const,
  label: "自分の納得を軸に",
  statement: "自分で選んだと言えることを積み重ねて生きていきたい。",
};

function selectProposal(): ReturnType<typeof usePurposeProposalsStore> {
  const store = usePurposeProposalsStore();
  store.setProposals([SELECTED_PROPOSAL]);
  store.select("SELF");
  return store;
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(createPurpose).mockReset();
});

describe("S-35", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("選ばれた案が無ければS-31へ差し戻す", async () => {
    mount(S35View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-31");
  });

  it("選ばれた案の一文を編集欄の初期値にする", () => {
    selectProposal();

    const wrapper = mount(S35View);

    const textarea = wrapper.find("#s35-statement").element as HTMLTextAreaElement;
    expect(textarea.value).toBe(SELECTED_PROPOSAL.statement);
    expect(wrapper.text()).toContain(`${SELECTED_PROPOSAL.statement.length} / 60`);
  });

  it("空文字では「これで確定する」が無効", async () => {
    selectProposal();
    const wrapper = mount(S35View);

    await wrapper.find("#s35-statement").setValue("");

    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("一文を書くと、確定できます");
  });

  it("確定するとPOST /purposesを呼び、成功したら一文を大きく見せる状態に切り替わる", async () => {
    const choicesStore = usePurposeChoicesStore();
    choicesStore.setAnswers({
      values: ["GROWTH"],
      fulfillingMoments: ["SELF_DETERMINED"],
      idealDailyLife: "HAVING_OPTIONS",
    });
    const dialogueStore = usePurposeDialogueStore();
    dialogueStore.addMessage({ role: "AI", body: "こんにちは" });
    selectProposal();
    vi.mocked(createPurpose).mockResolvedValue({
      version: 1,
      statement: "自分で選んだと言える選択を積み重ねていきたい。",
      selected_direction: "SELF",
      selected_label: "自分の納得を軸に",
      created_at: "2026-08-16T00:00:00Z",
    });

    const wrapper = mount(S35View);
    await wrapper.find("#s35-statement").setValue("自分で選んだと言える選択を積み重ねていきたい。");
    await wrapper.find("button[type='button'].app-button--primary").trigger("click");
    await flushPromises();

    expect(createPurpose).toHaveBeenCalledWith({
      choices: choicesStore.asChoices,
      messages: dialogueStore.messages,
      selected_direction: "SELF",
      selected_label: "自分の納得を軸に",
      original_statement: SELECTED_PROPOSAL.statement,
      statement: "自分で選んだと言える選択を積み重ねていきたい。",
    });
    expect(wrapper.text()).toContain("自分で選んだと言える選択を積み重ねていきたい。");
    expect(wrapper.find(".app-header-flow__nav").exists()).toBe(false);

    await wrapper.find("button[type='button'].app-button--primary").trigger("click");
    expect(push).toHaveBeenCalledWith("/s-50");
  });

  it("失敗したら同じ画面にエラーを表示し、入力内容を消さない", async () => {
    selectProposal();
    vi.mocked(createPurpose).mockRejectedValue(
      new ApiError(422, "STATEMENT_TOO_LONG", "statement must be 1-60 chars"),
    );

    const wrapper = mount(S35View);
    await wrapper.find("#s35-statement").setValue("書き直した一文");
    await wrapper.find("button[type='button'].app-button--primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("文字数が上限を超えています");
    expect((wrapper.find("#s35-statement").element as HTMLTextAreaElement).value).toBe(
      "書き直した一文",
    );
  });

  it("「案を選び直す」でS-34へ戻る", async () => {
    selectProposal();
    const wrapper = mount(S35View);

    await wrapper.find(".s35__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-34");
  });

  it("‹戻るでS-34へ戻る", async () => {
    selectProposal();
    const wrapper = mount(S35View);

    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-34");
  });
});
