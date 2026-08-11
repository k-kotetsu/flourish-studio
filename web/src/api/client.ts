/**
 * fetchラッパ。09_API設計2章・スキルflourish-api。
 * `fs_guest`/`fs_session`はHttpOnly Cookieなのでcredentials:"include"のみで足り、
 * トークン自体をJSからは扱わない(BFF方式)。
 */

const API_BASE = "/api/v1";

interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;
  readonly retryAfterSeconds?: number;

  constructor(
    status: number,
    code: string,
    message: string,
    options?: { details?: unknown; retryAfterSeconds?: number },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = options?.details;
    this.retryAfterSeconds = options?.retryAfterSeconds;
  }
}

export interface RequestOptions {
  idempotencyKey?: string;
  signal?: AbortSignal;
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** 401(UNAUTHENTICATED)を受け取ったときの共通処理。S-01へ戻す遷移はこれを介して呼び出し元(router)に委ねる。 */
let unauthorizedHandler: (() => void) | null = null;

export function onUnauthorized(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

async function request<T>(
  method: Method,
  path: string,
  body: unknown,
  options: RequestOptions,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: "include",
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw cause;
    }
    throw new ApiError(0, "NETWORK_ERROR", "network request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = (payload as { error?: ApiErrorBody } | null)?.error ?? {
      code: "UNKNOWN_ERROR",
      message: response.statusText,
    };
    const retryAfterHeader = response.headers.get("Retry-After");

    if (response.status === 401) {
      unauthorizedHandler?.();
    }

    throw new ApiError(response.status, errorBody.code, errorBody.message, {
      details: errorBody.details,
      retryAfterSeconds: retryAfterHeader ? Number(retryAfterHeader) : undefined,
    });
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, options: RequestOptions = {}): Promise<T> =>
    request<T>("GET", path, undefined, options),
  post: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    request<T>("POST", path, body, options),
  put: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    request<T>("PUT", path, body, options),
  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    request<T>("PATCH", path, body, options),
  delete: <T>(path: string, options: RequestOptions = {}): Promise<T> =>
    request<T>("DELETE", path, undefined, options),
};
