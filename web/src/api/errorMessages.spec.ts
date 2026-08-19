import { describe, expect, it } from "vitest";
import { messageForCode } from "./errorMessages";

const FORBIDDEN_WORDS = [
  "診断",
  "未完成",
  "空欄",
  "未入力",
  "頑張っていますね",
  "素晴らしい",
  "よくできています",
];

describe("messageForCode", () => {
  it("既知のcodeには具体的な文言を返す", () => {
    expect(messageForCode("UNAUTHENTICATED")).toContain("ログイン");
    expect(messageForCode("RATE_LIMITED")).not.toBe("");
    expect(messageForCode("EMAIL_TAKEN")).toContain("登録");
    expect(messageForCode("WEAK_PASSWORD")).not.toBe("");
  });

  it("未知のcodeはフォールバック文言に落ちる", () => {
    expect(messageForCode("SOME_FUTURE_CODE")).toBe(
      "うまくいきませんでした。もう一度試してみてください。",
    );
  });

  it("どの文言も謝罪語・感嘆符・禁止語を含まない(flourish-tone)", () => {
    const codes = [
      "UNAUTHENTICATED",
      "INVALID_CREDENTIALS",
      "EMAIL_TAKEN",
      "WEAK_PASSWORD",
      "JOB_NOT_FOUND",
      "JOB_FORBIDDEN",
      "RATE_LIMITED",
      "AI_PROVIDER_ERROR",
      "AI_OUTPUT_INVALID",
      "AI_REFUSED",
      "AI_MAX_TOKENS",
      "ANSWERS_INCOMPLETE",
      "STATEMENT_TOO_LONG",
      "GOALS_REQUIRED",
      "PURPOSE_REQUIRED",
      "NO_GOALS",
      "NETWORK_ERROR",
      "UNKNOWN",
    ];

    for (const code of codes) {
      const message = messageForCode(code);
      expect(message).not.toContain("申し訳");
      expect(message).not.toContain("すみません");
      expect(message).not.toContain("!");
      expect(message).not.toContain("！");
      for (const word of FORBIDDEN_WORDS) {
        expect(message).not.toContain(word);
      }
    }
  });
});
