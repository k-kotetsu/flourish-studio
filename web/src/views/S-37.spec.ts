import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S37View from "./S-37.vue";
import { getCurrentPurpose, updateCurrentPurpose } from "../api/purposes";
import { ApiError } from "../api/client";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/purposes", () => ({
  getCurrentPurpose: vi.fn(),
  updateCurrentPurpose: vi.fn(),
}));

const PURPOSE = {
  version: 1,
  statement: "自分で選んだと言えることを積み重ねて生きていきたい。",
  selected_direction: "SELF" as const,
  selected_label: "自分の納得を軸に",
  created_at: "2026-08-07T05:00:00Z",
};

afterEach(() => {
  push.mockReset();
  vi.mocked(getCurrentPurpose).mockReset();
  vi.mocked(updateCurrentPurpose).mockReset();
});

describe("S-37", () => {
  it("現在の一文を編集欄の初期値にする", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S37View);
    await flushPromises();

    const textarea = wrapper.find("#s37-statement").element as HTMLTextAreaElement;
    expect(textarea.value).toBe(PURPOSE.statement);
    expect(wrapper.text()).toContain(`${PURPOSE.statement.length} / 60`);
  });

  it("取得に失敗したらエラーを表示し、フォームは出さない", async () => {
    vi.mocked(getCurrentPurpose).mockRejectedValue(
      new ApiError(404, "PURPOSE_NOT_FOUND", "purpose has not been created yet"),
    );

    const wrapper = mount(S37View);
    await flushPromises();

    expect(wrapper.text()).toContain("うまくいきませんでした");
    expect(wrapper.find("#s37-statement").exists()).toBe(false);
  });

  it("空文字では「保存する」が無効", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S37View);
    await flushPromises();

    await wrapper.find("#s37-statement").setValue("");

    const submit = wrapper.find("button[type='button'].app-button--primary");
    expect(submit.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("一文を書くと、保存できます");
  });

  it("保存するとPUT /purposes/currentを呼び、成功したらS-36へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(updateCurrentPurpose).mockResolvedValue({
      ...PURPOSE,
      version: 2,
      statement: "書き換えた一文",
    });
    const wrapper = mount(S37View);
    await flushPromises();

    await wrapper.find("#s37-statement").setValue("書き換えた一文");
    await wrapper.find("button[type='button'].app-button--primary").trigger("click");
    await flushPromises();

    expect(updateCurrentPurpose).toHaveBeenCalledWith("書き換えた一文");
    expect(push).toHaveBeenCalledWith("/s-36");
  });

  it("保存に失敗したら同じ画面にエラーを表示し、入力内容を消さない", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    vi.mocked(updateCurrentPurpose).mockRejectedValue(
      new ApiError(422, "STATEMENT_TOO_LONG", "statement must be 1-60 chars"),
    );
    const wrapper = mount(S37View);
    await flushPromises();

    await wrapper.find("#s37-statement").setValue("書き換えた一文");
    await wrapper.find("button[type='button'].app-button--primary").trigger("click");
    await flushPromises();

    expect(push).not.toHaveBeenCalledWith("/s-36");
    expect(wrapper.text()).toContain("文字数が上限を超えています");
    expect((wrapper.find("#s37-statement").element as HTMLTextAreaElement).value).toBe(
      "書き換えた一文",
    );
  });

  it("‹戻るでS-36へ戻る", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S37View);
    await flushPromises();

    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-36");
  });
});
