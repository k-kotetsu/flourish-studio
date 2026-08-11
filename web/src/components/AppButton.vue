<script setup lang="ts">
/**
 * 07_デザイン原則 7.1。4種：主要／副次／テキスト／無効。
 * 無効は disabled で切り替える（表示のみでなく実際に押せなくする）。
 * 無効時の理由文言はこのコンポーネントの外（呼び出し側）で直下に置く。
 */
withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "text";
    disabled?: boolean;
    type?: "button" | "submit";
  }>(),
  {
    variant: "primary",
    disabled: false,
    type: "button",
  },
);

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<template>
  <button
    :type="type"
    class="app-button"
    :class="`app-button--${variant}`"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.app-button {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-button);
  font-family: inherit;
  font-size: var(--font-size-body);
  font-weight: 600;
  line-height: 1.4;
  min-height: var(--tap-target-min);
  cursor: pointer;
}

.app-button:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.app-button--primary {
  background: var(--primary);
  color: var(--primary-ink);
  border: none;
}

.app-button--secondary {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--control-border);
  font-weight: 500;
}

.app-button--text {
  background: transparent;
  color: var(--text-sub);
  border: none;
  font-weight: 500;
  width: auto;
  padding: var(--space-2) var(--space-3);
}

.app-button:disabled {
  background: var(--surface-sub);
  color: var(--text-faint);
  border-color: var(--surface-sub);
  cursor: default;
}
</style>
