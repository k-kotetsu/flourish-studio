/**
 * `POST /guest-sessions`。09_API設計5.1。S-11到達時に呼ぶ。
 * `fs_guest` はHttpOnly Cookieとしてサーバーが発行するため、レスポンスボディに値は乗らない。
 */
import { api } from "./client";

export function createGuestSession(): Promise<void> {
  return api.post<void>("/guest-sessions");
}
