<script setup lang="ts">
/**
 * ロゴマーク＋サービス名のロックアップ(P7-3、定義書19章 未決#4)。
 * ロゴマーク単体では意味を持たないため常に「Flourish Studio」と組みで使う、固定の並び。
 * `AppHeaderHub`のブランド表示(S-41ホームなど)で使う。
 */
import { LOGO_MARK_PATHS, LOGO_MARK_VIEW_BOX, SERVICE_NAME } from "../domain/logo";

withDefaults(
  defineProps<{
    size?: number;
  }>(),
  {
    size: 22,
  },
);
</script>

<template>
  <span class="app-logo">
    <svg
      class="app-logo__mark"
      :viewBox="LOGO_MARK_VIEW_BOX"
      :width="size"
      :height="size"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path
        v-for="(d, i) in LOGO_MARK_PATHS"
        :key="i"
        :d="d"
      />
    </svg>
    <span class="app-logo__wordmark">{{ SERVICE_NAME }}</span>
  </span>
</template>

<style scoped>
.app-logo {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.app-logo__mark {
  flex-shrink: 0;
}

.app-logo__wordmark {
  font-size: var(--font-size-section);
  font-weight: 700;
  font-family: var(--font-latin);
}
</style>
