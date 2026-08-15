<script setup lang="ts">
/**
 * 05_質問・コンテンツ設計2.2、07_デザイン原則7.5。5段階・横並びの目盛り。
 * 右がポジティブ。両端にのみラベルを表示し、5段階すべてに全文ラベルは付けない。
 * 操作部品の枠は`--control-border`を使う(flourish-ui「--borderとの混同」)。
 */
import type { Choice } from "../domain/questions";

const props = defineProps<{
  modelValue: number | null;
  choices: readonly Choice[];
  labelledBy: string;
  name: string;
}>();

defineEmits<{
  "update:modelValue": [value: number];
}>();
</script>

<template>
  <div class="scale-selector">
    <div
      class="scale-selector__row"
      role="radiogroup"
      :aria-labelledby="props.labelledBy"
    >
      <label
        v-for="choice in props.choices"
        :key="choice.score"
        class="scale-selector__cell"
        :class="{ 'scale-selector__cell--selected': modelValue === choice.score }"
      >
        <input
          type="radio"
          :name="name"
          class="scale-selector__input"
          :checked="modelValue === choice.score"
          @change="$emit('update:modelValue', choice.score)"
        >
      </label>
    </div>
    <div class="scale-selector__anchors">
      <span>{{ choices[0]?.label }}</span>
      <span>{{ choices[choices.length - 1]?.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.scale-selector__row {
  display: flex;
  gap: var(--space-1);
}

.scale-selector__cell {
  position: relative;
  flex: 1 1 0;
  min-height: var(--tap-target-min);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  cursor: pointer;
}

.scale-selector__cell--selected {
  border-color: var(--primary);
  background: var(--primary);
}

.scale-selector__cell:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.scale-selector__input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.scale-selector__anchors {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-1);
  font-size: var(--font-size-label);
  color: var(--text-faint);
}
</style>
