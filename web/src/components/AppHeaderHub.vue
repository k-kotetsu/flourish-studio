<script setup lang="ts">
/**
 * 07_デザイン原則 6.2「ハブ」型。S-41ホーム専用。戻るを置かない。
 * テーマ切替トグル自体はP4-9の担当。ここでは差し込み先のslotだけを用意する。
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
