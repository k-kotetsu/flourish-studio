/**
 * `POST /auth/login`。09_API設計5.5.1。S-02から呼ぶ。
 * `fs_session` はHttpOnly Cookieとしてサーバーが発行するため、レスポンスボディに値は乗らない。
 */
import { api } from "./client";

export function login(email: string, password: string): Promise<void> {
  return api.post<void>("/auth/login", { email, password });
}
