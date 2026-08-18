<script setup lang="ts">
/**
 * 07_デザイン原則 6.2「単独の画面」型（S-57/S-58など）。
 * プログレスバーを出さない点はどちらも共通で、左のアクションだけが戻る/中断/なしで切り替わる
 * (AppHeaderFlowのleftActionと同じ考え方)。S-61(P5-1)は「‹ 戻る」ではなく「× 中断」を使う
 * (wireframe-spec.md「S-61 WR回答 | × 中断 | 振り返り | − | −」)。
 * S-62/S-63(P5-2)は左アクション自体を持たない
 * (mockup.html `waiting()`/`s63()`のhdr呼び出しに`nav`が無い。タイトルのみ)。
 * 既定は`back`とし、既存の呼び出し元(S-36/S-37/S-57/S-58)の見た目・挙動は変えない。
 */
withDefaults(
  defineProps<{
    title: string;
    leftAction?: "back" | "cancel" | "none";
  }>(),
  {
    leftAction: "back",
  },
);

defineEmits<{
  back: [];
  cancel: [];
}>();
</script>

<template>
  <header class="app-header-single">
    <button
      v-if="leftAction === 'back'"
      type="button"
      class="app-header-single__nav"
      aria-label="戻る"
      @click="$emit('back')"
    >
      ‹ 戻る
    </button>
    <button
      v-else-if="leftAction === 'cancel'"
      type="button"
      class="app-header-single__nav"
      aria-label="中断"
      @click="$emit('cancel')"
    >
      × 中断
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
