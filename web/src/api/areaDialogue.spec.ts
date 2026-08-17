import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AreaDialogueError, streamAreaDialogue } from "./areaDialogue";

const CHOICES = [
  { question_code: "Q1" as const, option_codes: ["CAREER_OUTLOOK"] },
  { question_code: "Q2" as const, option_codes: ["CAREER_VALUE_GROWTH"] },
  { question_code: "Q3" as const, option_codes: ["CAREER_POSITION_GROWTH"] },
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

describe("streamAreaDialogue", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("/api/v1/ai/area-dialogueをcredentials:includeでPOSTし、areaを含める", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse(['event: done\ndata: {"turn": 1, "remaining": 1, "safety_flag": false}\n\n']),
    );

    await streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/ai/area-dialogue");
    expect(init?.credentials).toBe("include");
    expect(init?.body).toBe(JSON.stringify({ area: "CAREER", choices: CHOICES, messages: [] }));
  });

  it("deltaイベントごとにonDeltaを呼び、doneの内容を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse([
        'event: delta\ndata: {"text": "つながっていますね"}\n\n',
        'event: done\ndata: {"turn": 2, "remaining": 0, "safety_flag": false}\n\n',
      ]),
    );
    const onDelta = vi.fn();

    const result = await streamAreaDialogue("CAREER", CHOICES, [], { onDelta });

    expect(onDelta).toHaveBeenCalledWith("つながっていますね");
    expect(result).toEqual({ turn: 2, remaining: 0, safety_flag: false });
  });

  it("errorイベントはAreaDialogueErrorとして投げる", async () => {
    vi.mocked(fetch).mockResolvedValue(
      sseResponse(['event: error\ndata: {"code": "AI_REFUSED"}\n\n']),
    );

    await expect(streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} })).rejects
      .toMatchObject({ code: "AI_REFUSED" });
  });

  it("done/errorのどちらも受け取れずストリームが終わったらAI_PROVIDER_ERRORにする", async () => {
    vi.mocked(fetch).mockResolvedValue(sseResponse(['event: delta\ndata: {"text": "途中"}\n\n']));

    await expect(
      streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} }),
    ).rejects.toMatchObject({ code: "AI_PROVIDER_ERROR" });
  });

  it("ストリーム開始前の失敗(409 PURPOSE_REQUIRED等)はJSON応答のcodeをそのまま使う", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(409, { error: { code: "PURPOSE_REQUIRED", message: "no purpose" } }),
    );

    const error = await streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} }).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(AreaDialogueError);
    expect(error).toMatchObject({ code: "PURPOSE_REQUIRED" });
  });

  it("fetch自体が失敗したらAI_PROVIDER_ERRORとして投げる", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("network down"));

    await expect(
      streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} }),
    ).rejects.toMatchObject({ code: "AI_PROVIDER_ERROR" });
  });

  it("AbortErrorはAreaDialogueErrorに包まずそのまま伝える", async () => {
    const abortError = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValue(abortError);

    await expect(streamAreaDialogue("CAREER", CHOICES, [], { onDelta: () => {} })).rejects.toBe(
      abortError,
    );
  });
});
