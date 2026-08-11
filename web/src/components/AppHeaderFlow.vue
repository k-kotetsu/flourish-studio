<script setup lang="ts">
/**
 * 07_デザイン原則 6.2「フロー内」「フローの入口」「生成中」型。
 * 左を back / cancel / none で切り替えるだけで、フロー中のヘッダーはすべてこの1つで賄える。
 * 生成中画面（S-13/S-15/S-33/S-53/S-62）は leftAction="none"・stepなしで使う（6.3）。
 */
import AppProgressBar from "./AppProgressBar.vue";

withDefaults(
  defineProps<{
    title: string;
    percent: number;
    leftAction?: "back" | "cancel" | "none";
    step?: string | null;
  }>(),
  {
    leftAction: "back",
    step: null,
  },
);

defineEmits<{
  back: [];
  cancel: [];
}>();
</script>

<template>
  <header class="app-header-flow">
    <div class="app-header-flow__bar">
      <button
        v-if="leftAction === 'back'"
        type="button"
        class="app-header-flow__nav"
        aria-label="戻る"
        @click="$emit('back')"
      >
        ‹ 戻る
      </button>
      <button
        v-else-if="leftAction === 'cancel'"
        type="button"
        class="app-header-flow__nav"
        aria-label="中断"
        @click="$emit('cancel')"
      >
        × 中断
      </button>
      <span class="app-header-flow__title">{{ title }}</span>
      <span
        v-if="step"
        class="app-header-flow__step"
      >{{ step }}</span>
    </div>
    <AppProgressBar :percent="percent" />
  </header>
</template>

<style scoped>
.app-header-flow__bar {
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--layout-gutter);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.app-header-flow__nav {
  background: none;
  border: none;
  padding: var(--space-1) 0;
  min-height: var(--tap-target-min);
  font-family: inherit;
  font-size: var(--font-size-body);
  color: var(--text);
  cursor: pointer;
}

.app-header-flow__nav:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.app-header-flow__title {
  font-size: var(--font-size-body);
  font-weight: 600;
}

.app-header-flow__step {
  margin-left: auto;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
