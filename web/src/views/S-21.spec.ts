import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S21View from "./S-21.vue";
import { register } from "../api/auth";
import { ApiError } from "../api/client";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/auth", () => ({
  register: vi.fn(),
}));

afterEach(() => {
  vi.mocked(register).mockReset();
  push.mockReset();
});

async function fillAndSubmit(
  wrapper: ReturnType<typeof mount>,
  email: string,
  password: string,
): Promise<void> {
  await wrapper.find("#s21-email").setValue(email);
  await wrapper.find("#s21-password").setValue(password);
  await wrapper.find("form").trigger("submit");
  await flushPromises();
}

describe("S-21", () => {
  it("成功したらemail・passwordでregister()を呼び、完了画面を挟まずS-31へ遷移する", async () => {
    vi.mocked(register).mockResolvedValue(undefined);
    const wrapper = mount(S21View);

    await fillAndSubmit(wrapper, "user@example.com", "correct-horse-battery-9");

    expect(register).toHaveBeenCalledWith("user@example.com", "correct-horse-battery-9");
    expect(push).toHaveBeenCalledWith("/s-31");
  });

  it("メール重複で失敗したら同じ画面にエラーを表示し、入力内容を消さない", async () => {
    vi.mocked(register).mockRejectedValue(
      new ApiError(409, "EMAIL_TAKEN", "email is already registered"),
    );
    const wrapper = mount(S21View);

    await fillAndSubmit(wrapper, "user@example.com", "correct-horse-battery-9");

    expect(push).not.toHaveBeenCalledWith("/s-31");
    expect(wrapper.text()).toContain("すでに登録されています");
    expect((wrapper.find("#s21-email").element as HTMLInputElement).value).toBe(
      "user@example.com",
    );
    expect((wrapper.find("#s21-password").element as HTMLInputElement).value).toBe(
      "correct-horse-battery-9",
    );
  });

  it("弱いパスワードで失敗したら同じ画面にエラーを表示する", async () => {
    vi.mocked(register).mockRejectedValue(
      new ApiError(422, "WEAK_PASSWORD", "password is on the common/breached password list"),
    );
    const wrapper = mount(S21View);

    await fillAndSubmit(wrapper, "user@example.com", "password");

    expect(push).not.toHaveBeenCalledWith("/s-31");
    expect(wrapper.text()).toContain("このパスワードは使えません");
  });

  it("ヘッダーの「‹ 戻る」でS-16へ遷移する", async () => {
    const wrapper = mount(S21View);

    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-16");
  });

  it("利用規約・プライバシーポリシーへのリンクを表示する", () => {
    const wrapper = mount(S21View);

    const links = wrapper.findAll(".s21__consent a");
    const hrefs = links.map((link) => link.attributes("href"));

    expect(hrefs).toContain("/terms-of-service");
    expect(hrefs).toContain("/privacy-policy");
  });
});
