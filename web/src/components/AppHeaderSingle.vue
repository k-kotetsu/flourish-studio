<script setup lang="ts">
/**
 * 07_デザイン原則 6.2「単独の画面」型（S-57/S-58など）。
 * 戻るのみを置き、フローではないためプログレスバーを出さない。
 */
defineProps<{
  title: string;
}>();

defineEmits<{
  back: [];
}>();
</script>

<template>
  <header class="app-header-single">
    <button
      type="button"
      class="app-header-single__nav"
      aria-label="戻る"
      @click="$emit('back')"
    >
      ‹ 戻る
    </button>
    <span class="app-header-single__title">{{ title }}</span>
  </header>
</template>

<style scoped>
.app-header-single {
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--layout-gutter);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.app-header-single__nav {
  background: none;
  border: none;
  padding: var(--space-1) 0;
  min-height: var(--tap-target-min);
  font-family: inherit;
  font-size: var(--font-size-body);
  color: var(--text);
  cursor: pointer;
}

.app-header-single__nav:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.app-header-single__title {
  font-size: var(--font-size-body);
  font-weight: 600;
}
</style>
