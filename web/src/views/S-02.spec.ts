import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S02View from "./S-02.vue";
import { login } from "../api/auth";
import { ApiError } from "../api/client";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/auth", () => ({
  login: vi.fn(),
}));

afterEach(() => {
  vi.mocked(login).mockReset();
  push.mockReset();
});

async function fillAndSubmit(
  wrapper: ReturnType<typeof mount>,
  email: string,
  password: string,
): Promise<void> {
  await wrapper.find("#s02-email").setValue(email);
  await wrapper.find("#s02-password").setValue(password);
  await wrapper.find("form").trigger("submit");
  await flushPromises();
}

describe("S-02", () => {
  it("成功したらemail・passwordでlogin()を呼び、S-41へ遷移する", async () => {
    vi.mocked(login).mockResolvedValue(undefined);
    const wrapper = mount(S02View);

    await fillAndSubmit(wrapper, "user@example.com", "correct-horse-battery-9");

    expect(login).toHaveBeenCalledWith("user@example.com", "correct-horse-battery-9");
    expect(push).toHaveBeenCalledWith("/s-41");
  });

  it("失敗したら同じ画面にエラーを表示し、入力内容を消さない", async () => {
    vi.mocked(login).mockRejectedValue(
      new ApiError(401, "INVALID_CREDENTIALS", "email or password is incorrect"),
    );
    const wrapper = mount(S02View);

    await fillAndSubmit(wrapper, "user@example.com", "wrong-password");

    expect(push).not.toHaveBeenCalledWith("/s-41");
    expect(wrapper.text()).toContain("メールアドレスまたはパスワードが違います");
    expect((wrapper.find("#s02-email").element as HTMLInputElement).value).toBe(
      "user@example.com",
    );
    expect((wrapper.find("#s02-password").element as HTMLInputElement).value).toBe(
      "wrong-password",
    );
  });

  it("ヘッダーの「‹ 戻る」でトップへ遷移する", async () => {
    const wrapper = mount(S02View);

    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/");
  });

  it("「トップに戻る」でトップへ遷移する", async () => {
    const wrapper = mount(S02View);

    await wrapper.find(".s02__footer button").trigger("click");

    expect(push).toHaveBeenCalledWith("/");
  });
});
