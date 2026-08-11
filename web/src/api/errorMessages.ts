/**
 * `code` → ユーザー向け文言のマッピング。09_API設計2.3「サーバーはユーザー向け文言を
 * 持たない」に対応する、クライアント側の唯一の変換場所。トーンはスキルflourish-tone。
 * 未知の`code`（今後追加されるもの含む）はFALLBACKに落ちる。
 */

const CODE_MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: "ログインが必要です。もう一度ログインしてみてください。",
  JOB_NOT_FOUND: "この処理は見つかりませんでした。最初からやり直してみてください。",
  JOB_FORBIDDEN: "この処理は開けませんでした。最初からやり直してみてください。",
  RATE_LIMITED: "少し時間を置いてから、もう一度試してみてください。",
  AI_PROVIDER_ERROR:
    "うまく作れませんでした。書いていただいた内容はそのまま残っています。もう一度試してみてください。",
  AI_OUTPUT_INVALID:
    "うまく作れませんでした。書いていただいた内容はそのまま残っています。もう一度試してみてください。",
  AI_REFUSED: "この内容からはうまく作れませんでした。書いていただいた内容を見直してみてください。",
  AI_MAX_TOKENS:
    "うまく作れませんでした。書いていただいた内容はそのまま残っています。もう一度試してみてください。",
  ANSWERS_INCOMPLETE: "まだ答えていない項目が残っています。",
  STATEMENT_TOO_LONG: "文字数が上限を超えています。少し短くしてみてください。",
  GOALS_REQUIRED: "目標を1つ以上選んでみてください。",
  PURPOSE_REQUIRED: "先にありたい姿を決めてみてください。",
  NO_GOALS: "まだ目標が登録されていません。",
  NETWORK_ERROR:
    "通信がうまくいきませんでした。書いていただいた内容はそのまま残っています。もう一度試してみてください。",
};

const FALLBACK_MESSAGE = "うまくいきませんでした。もう一度試してみてください。";

export function messageForCode(code: string): string {
  return CODE_MESSAGES[code] ?? FALLBACK_MESSAGE;
}
