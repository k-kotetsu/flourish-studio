/**
 * `POST /ai/area-dialogue`(SSE)。09_API設計6章、10_AIプロンプト設計4.5、スキルflourish-api。
 * `purposeDialogue.ts`(P3-6)と同じ考え方でSSEを直接読む。確定済みの「ありたい姿」は
 * リクエストに含めない(サーバーが`PURPOSE#CURRENT`から読む。`ai_area_dialogue.py`の判断)。
 */

const API_BASE = "/api/v1";

export type AreaSlug = "CAREER" | "FINANCIAL" | "PHYSICAL" | "SOCIAL";

export interface AreaDialogueChoice {
  question_code: "Q1" | "Q2" | "Q3";
  option_codes: string[];
}

export interface AreaDialogueMessage {
  role: "AI" | "USER";
  body: string;
}

export interface AreaDialogueDone {
  turn: number;
  remaining: number;
  safety_flag: boolean;
}

/** SSEの`error`イベント、または応答自体が失敗したときに投げる。`code`はerrorMessages.tsのAI系4種・PURPOSE_REQUIREDと対応する。 */
export class AreaDialogueError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(`area dialogue failed: ${code}`);
    this.name = "AreaDialogueError";
    this.code = code;
  }
}

export interface AreaDialogueCallbacks {
  /** `delta`イベントのたびに断片を渡す。呼び出し側が画面に逐次表示する(09_API設計3.2)。 */
  onDelta: (text: string) => void;
}

/**
 * S-52。1往復分のAI応答をストリーミングで受け取る。`onDelta`を断片ごとに呼び、
 * 成功時は`done`イベントの内容を返す。失敗時(`error`イベント、ネットワーク断、
 * ストリームが`done`/`error`のどちらも返さず終わった場合)は`AreaDialogueError`を投げる。
 * `AbortError`はそのまま伝播させる(purposeDialogue.tsと同じ扱い)。
 */
export async function streamAreaDialogue(
  area: AreaSlug,
  choices: AreaDialogueChoice[],
  messages: AreaDialogueMessage[],
  callbacks: AreaDialogueCallbacks,
  signal?: AbortSignal,
): Promise<AreaDialogueDone> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/ai/area-dialogue`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area, choices, messages }),
      signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw cause;
    }
    throw new AreaDialogueError("AI_PROVIDER_ERROR");
  }

  if (!response.ok || response.body === null) {
    throw new AreaDialogueError(await errorCodeFromJsonResponse(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const event = parseSseEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);

      if (event?.event === "delta") {
        callbacks.onDelta((event.data as { text: string }).text);
      } else if (event?.event === "done") {
        return event.data as AreaDialogueDone;
      } else if (event?.event === "error") {
        throw new AreaDialogueError((event.data as { code: string }).code);
      }
      boundary = buffer.indexOf("\n\n");
    }
  }

  // done/errorのどちらも受け取れないままストリームが終わった(接続断など)
  throw new AreaDialogueError("AI_PROVIDER_ERROR");
}

async function errorCodeFromJsonResponse(response: Response): Promise<string> {
  // 401/409/422/429などストリーム開始前の失敗は通常のJSONエラー応答(09_API設計2.3)で返る。
  const payload: unknown = await response.json().catch(() => null);
  const code = (payload as { error?: { code?: string } } | null)?.error?.code;
  return code ?? "AI_PROVIDER_ERROR";
}

function parseSseEvent(raw: string): { event: string; data: unknown } | null {
  let event = "message";
  let data = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice("data:".length).trim();
    }
  }
  if (!data) return null;
  return { event, data: JSON.parse(data) };
}
