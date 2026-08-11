<script setup lang="ts">
/**
 * 07_デザイン原則 6.3。フロー全体に対する現在位置を示す。
 * 生成中画面は直前のステップの位置で止め、先へは進めない（percentはそのまま渡す）。
 */
const props = defineProps<{
  percent: number;
}>();
</script>

<template>
  <div
    class="app-progress-bar"
    role="progressbar"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-valuenow="props.percent"
  >
    <div
      class="app-progress-bar__fill"
      :style="{ width: `${props.percent}%` }"
    />
  </div>
</template>

<style scoped>
.app-progress-bar {
  height: var(--progress-bar-height);
  background: var(--surface-sub);
}

.app-progress-bar__fill {
  height: 100%;
  background: var(--primary);
}
</style>
