/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vite.dev/config/
export default defineConfig({
  // "/app/*" 配下でCloudFrontから配信される(infra/lib/edge-stack.ts)。
  // "/assets/*" は公開サイト側のビヘイビアと衝突するため、ビルド成果物はbase配下に収める。
  base: "/app/",
  plugins: [vue()],
  test: {
    environment: "happy-dom",
    // Node 22+ の組み込みlocalStorageがglobalを奪い、happy-dom側の実装を隠してしまうため無効化する。
    execArgv: ["--no-experimental-webstorage"],
  },
})
