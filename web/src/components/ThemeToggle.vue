<script setup lang="ts">
/**
 * 07_デザイン原則 3.2。ホーム（S-41）のヘッダー右端専用のテーマ切替トグル。
 * タップで 自動 → ライト → ダーク → 自動 と循環し、現在の状態をラベルで示す。
 * アイコンは3状態とも線画だが、「自動」だけは3.2が明示する「半分が塗られた円」に
 * 従い右半分を塗りつぶす（7.6の塗りつぶし禁止は一般則。この1アイコンは3.2が個別に形を指定している）。
 */
import { computed } from "vue";
import { useThemeStore, type ThemeMode } from "../stores/theme";

const themeStore = useThemeStore();

const LABEL: Record<ThemeMode, string> = {
  auto: "システムに追従",
  light: "ライト固定",
  dark: "ダーク固定",
};

const label = computed(() => LABEL[themeStore.mode]);
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="`テーマ: ${label}。タップで切り替え`"
    @click="themeStore.cycle()"
  >
    <svg
      v-if="themeStore.mode === 'auto'"
      class="theme-toggle__icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="8"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
      />
      <path
        d="M12 4a8 8 0 0 1 0 16z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
    <svg
      v-else-if="themeStore.mode === 'light'"
      class="theme-toggle__icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="4.5"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
      />
      <path
        d="M12 3v2.4M12 18.6V21M21 12h-2.4M5.4 12H3M18.4 5.6l-1.7 1.7M7.3 16.7l-1.7 1.7M18.4 18.4l-1.7-1.7M7.3 7.3 5.6 5.6"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
      />
    </svg>
    <svg
      v-else
      class="theme-toggle__icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <span class="theme-toggle__label">{{ label }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  min-height: var(--tap-target-min);
  padding: 0 var(--space-1);
  border: none;
  border-radius: var(--radius-button);
  background: transparent;
  color: var(--text);
  font-family: inherit;
  cursor: pointer;
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.theme-toggle__icon {
  width: 24px;
  height: 24px;
  flex: none;
}

.theme-toggle__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  white-space: nowrap;
}
</style>
