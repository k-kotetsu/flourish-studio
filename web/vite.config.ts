/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vite.dev/config/
export default defineConfig({
  // "/app/*" 配下でCloudFrontから配信される(infra/lib/edge-stack.ts)。
  // "/assets/*" は公開サイト側のビヘイビアと衝突するため、ビルド成果物はbase配下に収める。
  base: "/app/",
  plugins: [vue()],
  server: {
    proxy: {
      // 本番はCloudFrontが同一オリジンで/api/v1/*をAPI Gatewayへ振り分ける(infra/lib/edge-stack.ts)。
      // ローカルはAPI(8080)とフロント(5173)が別ポートのため、devサーバー側で同じ経路を再現する。
      "/api/v1": "http://localhost:8080",
    },
  },
  test: {
    environment: "happy-dom",
    // Node 22+ の組み込みlocalStorageがglobalを奪い、happy-dom側の実装を隠してしまうため無効化する。
    execArgv: ["--no-experimental-webstorage"],
  },
})
