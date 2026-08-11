import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs["flat/recommended"],
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    // TypeScriptがコンパイル時に未定義参照を検出するため、ESLint側のno-undefは無効化する
    // (DOM組み込み型を defineEmits 等の型引数で参照すると誤検知するため。typescript-eslint公式の推奨設定)
    rules: {
      "no-undef": "off",
    },
  },
);
