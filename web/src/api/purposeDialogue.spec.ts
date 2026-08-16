import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PurposeDialogueError, streamPurposeDialogue } from "./purposeDialogue";

const CHOICES = [
  { question_code: "Q1" as const, option_codes: ["GROWTH"] },
  { question_code: "Q2" as const, option_codes: ["SELF_DETERMINED"] },
  { question_code: "Q3" as const, option_codes: ["HAVING_OPTIONS"] },
];

function sseResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("streamPurposeDialogue", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("/api/v1/ai/purpose-dialogueをcredentials:includeでPOSTする", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse(['event: done\ndata: {"turn": 1, "remaining": 2, "safety_flag": false}\n\n']),
    );

    await streamPurposeDialogue(CHOICES, [], { onDelta: () => {} });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/ai/purpose-dialogue");
    expect(init?.credentials).toBe("include");
    expect(init?.body).toBe(JSON.stringify({ choices: CHOICES, messages: [] }));
  });

  it("deltaイベントごとにonDeltaを呼び、doneの内容を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse([
        'event: delta\ndata: {"text": "「成長」を"}\n\n',
        'event: delta\ndata: {"text": "選ばれていました。"}\n\n',
        'event: done\ndata: {"turn": 1, "remaining": 2, "safety_flag": false}\n\n',
      ]),
    );
    const onDelta = vi.fn();

    const result = await streamPurposeDialogue(CHOICES, [], { onDelta });

    expect(onDelta.mock.calls).toEqual([["「成長」を"], ["選ばれていました。"]]);
    expect(result).toEqual({ turn: 1, remaining: 2, safety_flag: false });
  });

  it("イベントが複数チャンクに分割されて届いても解釈できる", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse([
        'event: delta\nda',
        'ta: {"text": "分割"}\n\n',
        'event: done\ndata: {"turn": 1, "remaining": 2, "safety_flag": false}\n\n',
      ]),
    );
    const onDelta = vi.fn();

    await streamPurposeDialogue(CHOICES, [], { onDelta });

    expect(onDelta).toHaveBeenCalledWith("分割");
  });

  it("errorイベントはPurposeDialogueErrorとして投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse(['event: error\ndata: {"code": "AI_REFUSED"}\n\n']),
    );

    await expect(streamPurposeDialogue(CHOICES, [], { onDelta: () => {} })).rejects.toMatchObject(
      { code: "AI_REFUSED" },
    );
  });

  it("done/errorのどちらも受け取れずストリームが終わったらAI_PROVIDER_ERRORにする", async () => {
    vi.mocked(fetch).mockResolvedValue(sseResponse(['event: delta\ndata: {"text": "途中"}\n\n']));

    await expect(
      streamPurposeDialogue(CHOICES, [], { onDelta: () => {} }),
    ).rejects.toMatchObject({ code: "AI_PROVIDER_ERROR" });
  });

  it("ストリーム開始前の失敗(401等)はJSON応答のcodeをそのまま使う", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(401, { error: { code: "UNAUTHENTICATED", message: "no session" } }),
    );

    const error = await streamPurposeDialogue(CHOICES, [], { onDelta: () => {} }).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(PurposeDialogueError);
    expect(error).toMatchObject({ code: "UNAUTHENTICATED" });
  });

  it("fetch自体が失敗したらAI_PROVIDER_ERRORとして投げる", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("network down"));

    await expect(
      streamPurposeDialogue(CHOICES, [], { onDelta: () => {} }),
    ).rejects.toMatchObject({ code: "AI_PROVIDER_ERROR" });
  });

  it("AbortErrorはPurposeDialogueErrorに包まずそのまま伝える", async () => {
    const abortError = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValue(abortError);

    await expect(streamPurposeDialogue(CHOICES, [], { onDelta: () => {} })).rejects.toBe(
      abortError,
    );
  });
});
