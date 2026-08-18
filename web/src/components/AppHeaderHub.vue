<script setup lang="ts">
/**
 * 07_デザイン原則 6.2「ハブ」型（S-41ホーム、S-50領域を選ぶなど）。戻るを置かない。
 * `right`スロットにはS-41のみ`ThemeToggle`（P4-9）を差し込む。3.2「ホーム以外の画面には
 * トグルを置かない」ため、このコンポーネント自体はテーマ切替を知らない汎用のslotのままにする。
 */
withDefaults(
  defineProps<{
    title?: string;
  }>(),
  {
    title: "Flourish Studio",
  },
);
</script>

<template>
  <header class="app-header-hub">
    <span class="app-header-hub__title">{{ title }}</span>
    <div class="app-header-hub__right">
      <slot name="right" />
    </div>
  </header>
</template>

<style scoped>
.app-header-hub {
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--layout-gutter);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.app-header-hub__title {
  font-size: var(--font-size-section);
  font-weight: 600;
}

.app-header-hub__right {
  margin-left: auto;
}
</style>
