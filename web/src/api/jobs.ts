/**
 * 非同期ジョブのポーリング。09_API設計3.1・5.15、スキルflourish-api「非同期ジョブ」。
 * ポーリング間隔は常にサーバーの`poll_after_ms`に従う。クライアントは固定値を持たない。
 * `GET /jobs/{id}`はQUEUED/RUNNING中、必ず`poll_after_ms`を返す（P2-5で`api/app/api/v1/jobs.py`に実装済み）。
 */

import { api } from "./client";

export interface JobError {
  code: string;
  retryable: boolean;
}

export class JobFailedError extends Error {
  readonly code: string;
  readonly retryable: boolean;

  constructor(error: JobError) {
    super(`job failed: ${error.code}`);
    this.name = "JobFailedError";
    this.code = error.code;
    this.retryable = error.retryable;
  }
}

interface JobStatusResponse<T> {
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";
  poll_after_ms?: number;
  result?: T;
  error?: JobError;
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason);
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

/**
 * `GET /jobs/{id}`を`poll_after_ms`の指示どおりの間隔で呼び続け、終了状態を待つ。
 * `initialPollAfterMs`にはジョブ登録時（`POST`の`202`応答）の`poll_after_ms`を渡す。
 * `SUCCEEDED`なら`result`を返し、`FAILED`なら`JobFailedError`を投げる。
 * `signal`のabortでポーリングを打ち切る（画面遷移・中断ダイアログでの離脱に対応）。
 */
export async function waitForJob<T>(
  jobId: string,
  initialPollAfterMs: number,
  signal?: AbortSignal,
): Promise<T> {
  let nextDelayMs = initialPollAfterMs;

  for (;;) {
    await wait(nextDelayMs, signal);
    const job = await api.get<JobStatusResponse<T>>(`/jobs/${jobId}`, { signal });

    if (job.status === "SUCCEEDED") {
      return job.result as T;
    }
    if (job.status === "FAILED") {
      throw new JobFailedError(job.error as JobError);
    }
    if (job.poll_after_ms === undefined) {
      throw new Error(
        `GET /jobs/${jobId} did not return poll_after_ms while status=${job.status}`,
      );
    }
    nextDelayMs = job.poll_after_ms;
  }
}
